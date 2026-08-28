"""The trading-agent runtime that connects a broker, policy, and risk model."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..mt5.base import Broker
from ..mt5.types import OrderSide
from .features import Features, compute_features
from .policy import Decision, IndicatorPolicy, Policy, Signal
from .risk import RiskConfig


@dataclass
class AgentReport:
    """Result of a simulated agent run."""

    symbol: str
    decisions: list[dict] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    trades: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


class TradingAgent:
    """Observe → decide → size → execute, against any :class:`Broker`."""

    def __init__(
        self,
        broker: Broker,
        symbol: str,
        policy: Policy | None = None,
        risk: RiskConfig | None = None,
        lookback: int = 250,
        fast_window: int = 20,
        slow_window: int = 50,
        rsi_window: int = 14,
        atr_window: int = 14,
        momentum_window: int = 10,
    ) -> None:
        self.broker = broker
        self.symbol = symbol
        self.policy = policy or IndicatorPolicy()
        self.risk = risk or RiskConfig()
        self.lookback = lookback
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.rsi_window = rsi_window
        self.atr_window = atr_window
        self.momentum_window = momentum_window

    def observe(self) -> Features:
        rates = self.broker.get_rates(self.symbol, self.lookback)
        return compute_features(
            rates,
            fast_window=self.fast_window,
            slow_window=self.slow_window,
            rsi_window=self.rsi_window,
            atr_window=self.atr_window,
            momentum_window=self.momentum_window,
        )

    def act(self, decision: Decision, features: Features) -> list[str]:
        """Execute a decision. Returns a list of human-readable actions taken."""
        actions: list[str] = []
        positions = self.broker.positions(self.symbol)

        if decision.signal is Signal.CLOSE:
            for pos in positions:
                res = self.broker.close_position(pos.ticket, comment="policy_exit")
                if res.ok:
                    actions.append(f"closed #{pos.ticket} @ {res.price:.2f}")
            return actions

        if decision.signal in (Signal.BUY, Signal.SELL) and not positions:
            side = OrderSide.BUY if decision.signal is Signal.BUY else OrderSide.SELL
            equity = self.broker.account().equity
            volume = self.risk.volume(equity, features)
            if volume <= 0:
                return ["skip: computed volume is zero"]
            sl, tp = self.risk.stops(decision.signal, features)
            res = self.broker.submit_order(
                self.symbol, side, volume, sl=sl, tp=tp, comment="policy_entry"
            )
            if res.ok:
                actions.append(
                    f"opened {side.value} {volume:g} @ {res.price:.2f} "
                    f"(sl {sl:.2f}, tp {tp:.2f})"
                )
            else:
                actions.append(f"order rejected: {res.comment}")
        return actions

    def run_once(self) -> tuple[Decision, Features, list[str]]:
        """Single observe→decide→act cycle (used for live one-shot runs)."""
        features = self.observe()
        positions = self.broker.positions(self.symbol)
        has_position = bool(positions)
        side = positions[0].side.value if has_position else None
        decision = self.policy.decide(features, has_position, side)
        actions = self.act(decision, features)
        return decision, features, actions

    def run(self, max_steps: int | None = None) -> AgentReport:
        """Replay a simulated broker bar-by-bar and produce a report.

        Requires a broker exposing ``step()`` (e.g. :class:`SimulatedBroker`).
        """
        if not hasattr(self.broker, "step"):
            raise TypeError("run() requires a stepping broker; use run_once() for live brokers")

        self.broker.connect()
        decisions: list[dict] = []
        times: list = []
        equity: list[float] = []
        steps = 0

        while True:
            features = self.observe()
            positions = self.broker.positions(self.symbol)
            has_position = bool(positions)
            side = positions[0].side.value if has_position else None
            decision = self.policy.decide(features, has_position, side)
            actions = self.act(decision, features)

            acct = self.broker.account()
            now = self.broker.current_time  # type: ignore[attr-defined]
            times.append(now)
            equity.append(acct.equity)
            decisions.append(
                {
                    "time": now,
                    "price": round(features.close, 4),
                    "signal": decision.signal.value,
                    "score": round(decision.score, 3),
                    "confidence": round(decision.confidence, 3),
                    "rsi": round(features.rsi, 1),
                    "equity": round(acct.equity, 2),
                    "actions": actions,
                    "reason": "; ".join(decision.reasons),
                }
            )

            steps += 1
            if max_steps is not None and steps >= max_steps:
                break
            if not self.broker.step():  # type: ignore[attr-defined]
                break

        # Close anything still open at the final price.
        for pos in self.broker.positions(self.symbol):
            self.broker.close_position(pos.ticket, comment="end_of_run")

        equity_curve = pd.Series(equity, index=pd.Index(times, name="time"), name="equity")
        trades = list(getattr(self.broker, "closed_positions", []))
        metrics = self._metrics(equity_curve, trades, decisions)
        return AgentReport(
            symbol=self.symbol,
            decisions=decisions,
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
        )

    def _metrics(self, equity: pd.Series, trades: list[dict], decisions: list[dict]) -> dict:
        initial = float(getattr(self.broker, "initial_balance", equity.iloc[0] if len(equity) else 0.0))
        final = float(equity.iloc[-1]) if len(equity) else initial
        wins = [t for t in trades if t["profit"] > 0]
        gross_profit = sum(t["profit"] for t in trades if t["profit"] > 0)
        gross_loss = -sum(t["profit"] for t in trades if t["profit"] < 0)
        if len(equity):
            running_max = equity.cummax()
            max_dd = float((equity / running_max - 1.0).min())
        else:
            max_dd = 0.0
        return {
            "initial_balance": round(initial, 2),
            "final_equity": round(final, 2),
            "total_return": round(final / initial - 1.0, 4) if initial else 0.0,
            "num_trades": len(trades),
            "win_rate": round(len(wins) / len(trades), 3) if trades else 0.0,
            "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss > 0 else None,
            "max_drawdown": round(max_dd, 4),
            "bars": len(decisions),
        }
