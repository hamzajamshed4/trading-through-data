"""An offline paper-trading broker that mimics the MetaTrader 5 API.

The broker replays a historical (or synthetic) OHLC series bar-by-bar. It fills
market orders at the current bar with a configurable spread, tracks open
positions, settles stop-loss / take-profit against each subsequent bar's
high/low range, and maintains balance and equity. This lets the trading agent
run end-to-end without a live terminal or broker account.
"""

from __future__ import annotations

import itertools

import pandas as pd

from .base import Broker
from .types import AccountInfo, OrderResult, OrderSide, Position, Tick


class SimulatedBroker(Broker):
    def __init__(
        self,
        prices: pd.DataFrame,
        symbol: str = "SYNTH",
        initial_balance: float = 10_000.0,
        spread_bps: float = 2.0,
        contract_size: float = 1.0,
        commission_per_trade: float = 0.0,
    ) -> None:
        required = {"open", "high", "low", "close"}
        if not required.issubset(prices.columns):
            raise ValueError(f"prices must contain columns {sorted(required)}")
        if len(prices) < 2:
            raise ValueError("need at least two bars to simulate")

        self._prices = prices.copy()
        self._prices["volume"] = self._prices.get("volume", 0.0)
        self.symbol = symbol
        self.initial_balance = float(initial_balance)
        self.balance = float(initial_balance)
        self.spread_bps = spread_bps
        self.contract_size = contract_size
        self.commission_per_trade = commission_per_trade

        self._i = 0
        self._positions: dict[int, Position] = {}
        self._tickets = itertools.count(1)
        self.closed_positions: list[dict] = []

    # -- clock -----------------------------------------------------------
    @property
    def current_time(self):
        return self._prices.index[self._i]

    @property
    def current_price(self) -> float:
        return float(self._prices["close"].iloc[self._i])

    def step(self) -> bool:
        """Advance one bar; settle SL/TP and profits. Returns False at the end."""
        if self._i >= len(self._prices) - 1:
            return False
        self._i += 1
        self._settle_bar()
        return True

    # -- market data -----------------------------------------------------
    def connect(self) -> bool:
        return True

    def shutdown(self) -> None:
        return None

    def get_rates(self, symbol: str, count: int) -> pd.DataFrame:
        start = max(0, self._i - count + 1)
        return self._prices.iloc[start : self._i + 1][["open", "high", "low", "close", "volume"]]

    def get_tick(self, symbol: str) -> Tick:
        mid = self.current_price
        half = mid * (self.spread_bps / 10_000.0) / 2.0
        return Tick(time=self.current_time, bid=mid - half, ask=mid + half)

    # -- account / positions --------------------------------------------
    def account(self) -> AccountInfo:
        unrealized = sum(p.profit for p in self._positions.values())
        return AccountInfo(balance=self.balance, equity=self.balance + unrealized)

    def positions(self, symbol: str | None = None) -> list[Position]:
        return [p for p in self._positions.values() if symbol is None or p.symbol == symbol]

    # -- orders ----------------------------------------------------------
    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        volume: float,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "",
    ) -> OrderResult:
        if volume <= 0:
            return OrderResult(ok=False, comment="volume must be positive")
        tick = self.get_tick(symbol)
        price = tick.ask if side is OrderSide.BUY else tick.bid
        ticket = next(self._tickets)
        self.balance -= self.commission_per_trade
        self._positions[ticket] = Position(
            ticket=ticket,
            symbol=symbol,
            side=side,
            volume=volume,
            entry_price=price,
            entry_time=self.current_time,
            sl=sl,
            tp=tp,
            profit=0.0,
        )
        return OrderResult(ok=True, ticket=ticket, price=price, comment=comment or "opened")

    def close_position(self, ticket: int, comment: str = "") -> OrderResult:
        pos = self._positions.get(ticket)
        if pos is None:
            return OrderResult(ok=False, comment="unknown ticket")
        tick = self.get_tick(pos.symbol)
        price = tick.bid if pos.side is OrderSide.BUY else tick.ask
        self._realize(pos, price, reason=comment or "manual")
        return OrderResult(ok=True, ticket=ticket, price=price, comment=comment or "closed")

    # -- internals -------------------------------------------------------
    def _pnl(self, pos: Position, price: float) -> float:
        return (price - pos.entry_price) * pos.side.sign * pos.volume * self.contract_size

    def _realize(self, pos: Position, price: float, reason: str) -> None:
        pnl = self._pnl(pos, price)
        self.balance += pnl - self.commission_per_trade
        self.closed_positions.append(
            {
                "ticket": pos.ticket,
                "side": pos.side.value,
                "volume": pos.volume,
                "entry_time": pos.entry_time,
                "entry_price": pos.entry_price,
                "exit_time": self.current_time,
                "exit_price": price,
                "profit": pnl,
                "reason": reason,
            }
        )
        del self._positions[pos.ticket]

    def _settle_bar(self) -> None:
        """Check SL/TP against the current bar's range and mark profits."""
        bar = self._prices.iloc[self._i]
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        for pos in list(self._positions.values()):
            hit_price: float | None = None
            reason = ""
            if pos.side is OrderSide.BUY:
                if pos.sl is not None and low <= pos.sl:
                    hit_price, reason = pos.sl, "stop_loss"
                elif pos.tp is not None and high >= pos.tp:
                    hit_price, reason = pos.tp, "take_profit"
            else:  # SELL
                if pos.sl is not None and high >= pos.sl:
                    hit_price, reason = pos.sl, "stop_loss"
                elif pos.tp is not None and low <= pos.tp:
                    hit_price, reason = pos.tp, "take_profit"

            if hit_price is not None:
                self._realize(pos, hit_price, reason=reason)
            else:
                pos.profit = self._pnl(pos, close)
