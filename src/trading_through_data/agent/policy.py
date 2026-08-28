"""Decision policies that turn features into trading actions.

The default :class:`IndicatorPolicy` blends three transparent signals — trend
(SMA relationship), momentum (rate of change), and mean-reversion pressure (RSI)
— into a single score in ``[-1, 1]`` with an explainable rationale. The
:class:`Policy` interface is deliberately small so an ML model or LLM-based
policy can be dropped in without touching the agent runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from .features import Features


class Signal(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


@dataclass
class Decision:
    """A policy's recommendation for the current bar."""

    signal: Signal
    score: float  # signed conviction in [-1, 1]
    confidence: float  # abs(score), in [0, 1]
    reasons: list[str] = field(default_factory=list)


class Policy(ABC):
    """Maps features (and current position state) to a :class:`Decision`."""

    @abstractmethod
    def decide(
        self,
        features: Features,
        has_position: bool = False,
        position_side: str | None = None,
    ) -> Decision:
        ...


@dataclass
class IndicatorPolicy(Policy):
    """A weighted blend of trend, momentum, and RSI signals."""

    entry_threshold: float = 0.35
    exit_threshold: float = 0.15
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    trend_weight: float = 0.5
    momentum_weight: float = 0.3
    rsi_weight: float = 0.2

    def _score(self, f: Features) -> tuple[float, list[str]]:
        reasons: list[str] = []

        # Trend: normalise the SMA gap by ATR so it is comparable across regimes.
        gap = f.sma_fast - f.sma_slow
        denom = f.atr if f.atr > 0 else abs(f.close) * 1e-4
        trend = max(-1.0, min(1.0, gap / (denom * 2.0)))
        reasons.append(
            f"trend {'up' if trend >= 0 else 'down'} (SMA fast {f.sma_fast:.2f} "
            f"vs slow {f.sma_slow:.2f})"
        )

        # Momentum: recent rate of change, squashed.
        momentum = max(-1.0, min(1.0, f.momentum * 20.0))
        reasons.append(f"momentum {f.momentum * 100:+.2f}%")

        # RSI: contrarian pressure near extremes.
        if f.rsi >= self.rsi_overbought:
            rsi_component = -1.0
            reasons.append(f"RSI {f.rsi:.0f} overbought")
        elif f.rsi <= self.rsi_oversold:
            rsi_component = 1.0
            reasons.append(f"RSI {f.rsi:.0f} oversold")
        else:
            rsi_component = (50.0 - f.rsi) / 50.0
            reasons.append(f"RSI {f.rsi:.0f} neutral")

        score = (
            self.trend_weight * trend
            + self.momentum_weight * momentum
            + self.rsi_weight * rsi_component
        )
        return max(-1.0, min(1.0, score)), reasons

    def decide(
        self,
        features: Features,
        has_position: bool = False,
        position_side: str | None = None,
    ) -> Decision:
        if not features.ready:
            return Decision(Signal.HOLD, 0.0, 0.0, ["warming up: not enough history"])

        score, reasons = self._score(features)
        confidence = abs(score)

        if has_position:
            # Exit when conviction fades or flips against the open position.
            if position_side == "buy" and score < self.exit_threshold:
                return Decision(Signal.CLOSE, score, confidence, ["long conviction faded", *reasons])
            if position_side == "sell" and score > -self.exit_threshold:
                return Decision(Signal.CLOSE, score, confidence, ["short conviction faded", *reasons])
            return Decision(Signal.HOLD, score, confidence, ["holding position", *reasons])

        if score >= self.entry_threshold:
            return Decision(Signal.BUY, score, confidence, reasons)
        if score <= -self.entry_threshold:
            return Decision(Signal.SELL, score, confidence, reasons)
        return Decision(Signal.HOLD, score, confidence, ["no strong edge", *reasons])
