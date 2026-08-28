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

    # Optional broker/instrument volume constraints (e.g. from MT5 symbol_info).
    # When set, the computed volume is snapped to ``volume_step`` and clamped to
    # ``[volume_min, volume_max]`` so live orders satisfy the symbol's rules.
    fixed_volume: float | None = None
    volume_min: float | None = None
    volume_step: float | None = None
    volume_max: float | None = None

    def stops(self, side: Signal, features: Features) -> tuple[float, float]:
        """Return absolute (stop_loss, take_profit) prices for a new position."""
        price = features.close
        stop_dist = self.atr_stop_mult * features.atr
        take_dist = self.atr_take_mult * features.atr
        if side is Signal.BUY:
            return price - stop_dist, price + take_dist
        return price + stop_dist, price - take_dist

    def normalize_volume(self, volume: float) -> float:
        """Snap a raw volume to the instrument's step and min/max bounds."""
        step = self.volume_step
        if step and step > 0:
            volume = round(volume / step) * step
        if self.volume_min is not None:
            volume = max(self.volume_min, volume)
        if self.volume_max is not None:
            volume = min(self.volume_max, volume)
        return round(volume, 8)

    def volume(self, equity: float, features: Features) -> float:
        """Size the position so the ATR-based stop risks ``risk_per_trade``.

        Falls back to the notional cap when the ATR-implied size would exceed
        it, then snaps to the instrument's volume step/bounds. When
        ``fixed_volume`` is set it overrides the risk-based sizing entirely.
        """
        if self.fixed_volume is not None:
            return self.normalize_volume(self.fixed_volume)

        stop_dist = self.atr_stop_mult * features.atr
        if stop_dist <= 0:
            return 0.0
        risk_amount = equity * self.risk_per_trade
        vol_by_risk = risk_amount / (stop_dist * self.contract_size)

        max_notional = equity * self.max_position_fraction
        vol_by_notional = max_notional / (features.close * self.contract_size)

        vol = max(0.0, min(vol_by_risk, vol_by_notional))
        return self.normalize_volume(round(vol, 4))
