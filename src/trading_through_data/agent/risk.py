"""Risk management: position sizing and stop-loss / take-profit placement."""

from __future__ import annotations

from dataclasses import dataclass

from .features import Features
from .policy import Signal


@dataclass
class RiskConfig:
    """Risk parameters applied to every trade.

    * ``risk_per_trade`` – fraction of equity risked between entry and stop.
    * ``atr_stop_mult`` / ``atr_take_mult`` – SL/TP distances in ATR multiples.
    * ``max_position_fraction`` – cap on notional as a fraction of equity.
    """

    risk_per_trade: float = 0.02
    atr_stop_mult: float = 2.0
    atr_take_mult: float = 3.0
    max_position_fraction: float = 1.0
    contract_size: float = 1.0

    def stops(self, side: Signal, features: Features) -> tuple[float, float]:
        """Return absolute (stop_loss, take_profit) prices for a new position."""
        price = features.close
        stop_dist = self.atr_stop_mult * features.atr
        take_dist = self.atr_take_mult * features.atr
        if side is Signal.BUY:
            return price - stop_dist, price + take_dist
        return price + stop_dist, price - take_dist

    def volume(self, equity: float, features: Features) -> float:
        """Size the position so the ATR-based stop risks ``risk_per_trade``.

        Falls back to the notional cap when the ATR-implied size would exceed it.
        """
        stop_dist = self.atr_stop_mult * features.atr
        if stop_dist <= 0:
            return 0.0
        risk_amount = equity * self.risk_per_trade
        vol_by_risk = risk_amount / (stop_dist * self.contract_size)

        max_notional = equity * self.max_position_fraction
        vol_by_notional = max_notional / (features.close * self.contract_size)

        vol = min(vol_by_risk, vol_by_notional)
        return max(0.0, round(vol, 4))
