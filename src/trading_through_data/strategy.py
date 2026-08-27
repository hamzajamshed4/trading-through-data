"""Trading-signal generation.

The reference strategy is a simple moving-average (SMA) crossover: go long when
the fast SMA is above the slow SMA, and flat otherwise. The module exposes the
intermediate SMAs so they can be plotted alongside the price.
"""

from __future__ import annotations

import pandas as pd


def sma_crossover_signals(
    prices: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    price_column: str = "close",
) -> pd.DataFrame:
    """Compute SMA-crossover positions for a price frame.

    Returns a DataFrame aligned to ``prices`` with columns:

    * ``price`` – the price column used for the strategy;
    * ``sma_fast`` / ``sma_slow`` – the moving averages;
    * ``position`` – desired exposure for the *next* bar (1 = long, 0 = flat).

    The position is shifted by one bar so signals generated from a bar's close
    are only acted upon on the following bar, avoiding look-ahead bias.
    """
    if fast_window <= 0 or slow_window <= 0:
        raise ValueError("window lengths must be positive")
    if fast_window >= slow_window:
        raise ValueError("fast_window must be smaller than slow_window")
    if price_column not in prices.columns:
        raise ValueError(f"price column {price_column!r} not found in frame")

    price = prices[price_column]
    sma_fast = price.rolling(window=fast_window, min_periods=fast_window).mean()
    sma_slow = price.rolling(window=slow_window, min_periods=slow_window).mean()

    raw_signal = (sma_fast > sma_slow).astype(int)
    # Only take positions once both SMAs are defined.
    raw_signal[sma_slow.isna()] = 0
    position = raw_signal.shift(1).fillna(0).astype(int)

    return pd.DataFrame(
        {
            "price": price,
            "sma_fast": sma_fast,
            "sma_slow": sma_slow,
            "position": position,
        }
    )
