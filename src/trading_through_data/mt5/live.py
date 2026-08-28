"""Live MetaTrader 5 broker backed by the ``MetaTrader5`` package.

The ``MetaTrader5`` package ships Windows-only wheels and requires a running MT5
terminal plus a broker account. It is therefore an *optional* dependency: import
it lazily and raise a clear, actionable error when it is unavailable so the rest
of the toolkit (and the simulated broker) works everywhere.

Install with ``pip install "trading-through-data[mt5]"`` on Windows, then run the
agent with ``--mode live`` and MT5 credentials.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from .base import Broker
from .types import AccountInfo, OrderResult, OrderSide, Position, Tick

_IMPORT_ERROR_HINT = (
    "The 'MetaTrader5' package is required for live trading but is not "
    "installed/available (it provides Windows-only wheels and needs a running "
    "MetaTrader 5 terminal). Install it on Windows with "
    "'pip install \"trading-through-data[mt5]\"'. For development on Linux/macOS "
    "use the simulated broker (mode='simulated')."
)


def _import_mt5():
    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only off-Windows
        raise RuntimeError(_IMPORT_ERROR_HINT) from exc
    return mt5


class MetaTrader5Broker(Broker):
    """Thin adapter over the ``MetaTrader5`` API implementing :class:`Broker`."""

    def __init__(
        self,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        path: str | None = None,
        timeframe: str = "H1",
    ) -> None:
        self._mt5 = _import_mt5()
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.timeframe = timeframe

    def _tf_const(self):
        name = f"TIMEFRAME_{self.timeframe.upper()}"
        const = getattr(self._mt5, name, None)
        if const is None:
            raise ValueError(f"unknown MT5 timeframe: {self.timeframe!r}")
        return const

    def connect(self) -> bool:
        kwargs = {}
        if self.path:
            kwargs["path"] = self.path
        if self.login is not None:
            kwargs.update(login=int(self.login), password=self.password, server=self.server)
        if not self._mt5.initialize(**kwargs):
            code, msg = self._mt5.last_error()
            raise RuntimeError(f"MT5 initialize failed ({code}): {msg}")
        return True

    def shutdown(self) -> None:
        self._mt5.shutdown()

    def get_rates(self, symbol: str, count: int) -> pd.DataFrame:
        rates = self._mt5.copy_rates_from_pos(symbol, self._tf_const(), 0, count)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"no rates returned for {symbol}")
        frame = pd.DataFrame(rates)
        frame["time"] = pd.to_datetime(frame["time"], unit="s")
        frame = frame.set_index("time")
        frame = frame.rename(columns={"tick_volume": "volume"})
        cols = [c for c in ("open", "high", "low", "close", "volume") if c in frame.columns]
        return frame[cols]

    def get_tick(self, symbol: str) -> Tick:
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"no tick for {symbol}")
        return Tick(time=datetime.fromtimestamp(tick.time), bid=tick.bid, ask=tick.ask)

    def account(self) -> AccountInfo:
        info = self._mt5.account_info()
        if info is None:
            raise RuntimeError("account_info() returned None")
        return AccountInfo(
            balance=info.balance,
            equity=info.equity,
            currency=getattr(info, "currency", "USD"),
            leverage=getattr(info, "leverage", 100),
        )

    def positions(self, symbol: str | None = None) -> list[Position]:
        raw = self._mt5.positions_get(symbol=symbol) if symbol else self._mt5.positions_get()
        result: list[Position] = []
        for p in raw or []:
            side = OrderSide.BUY if p.type == self._mt5.POSITION_TYPE_BUY else OrderSide.SELL
            result.append(
                Position(
                    ticket=p.ticket,
                    symbol=p.symbol,
                    side=side,
                    volume=p.volume,
                    entry_price=p.price_open,
                    entry_time=datetime.fromtimestamp(p.time),
                    sl=p.sl or None,
                    tp=p.tp or None,
                    profit=p.profit,
                )
            )
        return result

    def symbol_spec(self, symbol: str) -> dict:
        """Return the instrument's contract size, volume rules, and precision.

        Also selects the symbol into Market Watch so quotes/orders work.
        """
        mt5 = self._mt5
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"could not select symbol {symbol!r} in Market Watch")
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"no symbol_info for {symbol!r}")
        return {
            "contract_size": float(getattr(info, "trade_contract_size", 1.0)),
            "volume_min": float(info.volume_min),
            "volume_step": float(info.volume_step),
            "volume_max": float(info.volume_max),
            "digits": int(info.digits),
            "point": float(info.point),
        }

    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        volume: float,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "",
    ) -> OrderResult:
        mt5 = self._mt5
        spec = self.symbol_spec(symbol)
        digits = spec["digits"]

        # Snap volume to the symbol's step and clamp to its min/max bounds so the
        # broker does not reject the order with "invalid volume".
        step = spec["volume_step"]
        if step > 0:
            volume = round(volume / step) * step
        volume = max(spec["volume_min"], min(volume, spec["volume_max"]))
        volume = round(volume, 8)
        if volume <= 0:
            return OrderResult(ok=False, comment="normalized volume is zero")

        tick = mt5.symbol_info_tick(symbol)
        price = round(tick.ask if side is OrderSide.BUY else tick.bid, digits)
        order_type = mt5.ORDER_TYPE_BUY if side is OrderSide.BUY else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "deviation": 20,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "comment": comment or "ttd-agent",
        }
        if sl is not None:
            request["sl"] = round(float(sl), digits)
        if tp is not None:
            request["tp"] = round(float(tp), digits)
        result = mt5.order_send(request)
        ok = result is not None and result.retcode == mt5.TRADE_RETCODE_DONE
        return OrderResult(
            ok=ok,
            ticket=getattr(result, "order", None),
            price=getattr(result, "price", None),
            comment=getattr(result, "comment", "") or "",
        )

    def close_position(self, ticket: int, comment: str = "") -> OrderResult:
        mt5 = self._mt5
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return OrderResult(ok=False, comment="unknown ticket")
        pos = positions[0]
        symbol = pos.symbol
        tick = mt5.symbol_info_tick(symbol)
        if pos.type == mt5.POSITION_TYPE_BUY:
            close_type, price = mt5.ORDER_TYPE_SELL, tick.bid
        else:
            close_type, price = mt5.ORDER_TYPE_BUY, tick.ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "comment": comment or "ttd-agent-close",
        }
        result = mt5.order_send(request)
        ok = result is not None and result.retcode == mt5.TRADE_RETCODE_DONE
        return OrderResult(ok=ok, ticket=ticket, price=getattr(result, "price", None),
                           comment=getattr(result, "comment", "") or "")
