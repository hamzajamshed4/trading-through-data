"""Technical-indicator feature extraction for the agent's policy."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Features:
    """Latest indicator readings derived from a window of OHLC bars."""

    close: float
    sma_fast: float
    sma_slow: float
    rsi: float
    atr: float
    momentum: float
    ready: bool


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _atr(rates: pd.DataFrame, window: int) -> pd.Series:
    high, low, close = rates["high"], rates["low"], rates["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()


def compute_features(
    rates: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    rsi_window: int = 14,
    atr_window: int = 14,
    momentum_window: int = 10,
) -> Features:
    """Compute the latest :class:`Features` from a window of OHLC bars."""
    close = rates["close"]
    sma_fast = close.rolling(fast_window, min_periods=fast_window).mean()
    sma_slow = close.rolling(slow_window, min_periods=slow_window).mean()
    rsi = _rsi(close, rsi_window)
    atr = _atr(rates, atr_window)
    momentum = close.pct_change(momentum_window)

    last_close = float(close.iloc[-1])
    last_fast = sma_fast.iloc[-1]
    last_slow = sma_slow.iloc[-1]
    last_atr = atr.iloc[-1]

    ready = bool(
        len(rates) >= slow_window
        and not pd.isna(last_fast)
        and not pd.isna(last_slow)
        and not pd.isna(last_atr)
        and last_atr > 0
    )

    return Features(
        close=last_close,
        sma_fast=float(last_fast) if not pd.isna(last_fast) else last_close,
        sma_slow=float(last_slow) if not pd.isna(last_slow) else last_close,
        rsi=float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0,
        atr=float(last_atr) if not pd.isna(last_atr) else 0.0,
        momentum=float(momentum.iloc[-1]) if not pd.isna(momentum.iloc[-1]) else 0.0,
        ready=ready,
    )
