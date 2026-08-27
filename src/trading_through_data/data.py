"""Price-data acquisition for the backtester.

Two sources are supported:

* :func:`generate_price_data` produces a deterministic synthetic price series
  using a geometric random walk. It requires no network access, which keeps the
  development environment reproducible and offline-friendly.
* :func:`load_price_data` reads an OHLC CSV file exported from a data provider.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_price_data(
    symbol: str = "SYNTH",
    days: int = 365,
    start: str = "2023-01-01",
    seed: int = 42,
    start_price: float = 100.0,
    annual_drift: float = 0.08,
    annual_volatility: float = 0.30,
) -> pd.DataFrame:
    """Generate a deterministic synthetic daily OHLC price series.

    The close price follows a geometric random walk; open/high/low are derived
    around each close so the frame mirrors the shape of real market data.

    Returns a DataFrame indexed by date with columns
    ``[open, high, low, close, volume]`` and a ``symbol`` attribute.
    """
    if days <= 0:
        raise ValueError("days must be a positive integer")

    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, periods=days)

    dt = 1.0 / 252.0
    drift = (annual_drift - 0.5 * annual_volatility**2) * dt
    diffusion = annual_volatility * np.sqrt(dt)
    shocks = rng.standard_normal(days)
    log_returns = drift + diffusion * shocks

    close = start_price * np.exp(np.cumsum(log_returns))
    prev_close = np.concatenate([[start_price], close[:-1]])

    intraday = np.abs(rng.standard_normal(days)) * diffusion * close
    open_ = prev_close
    high = np.maximum(open_, close) + intraday
    low = np.minimum(open_, close) - intraday
    volume = rng.integers(1_000_000, 5_000_000, size=days)

    frame = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )
    frame.index.name = "date"
    frame.attrs["symbol"] = symbol
    return frame


def load_price_data(path: str | Path, symbol: str | None = None) -> pd.DataFrame:
    """Load an OHLC CSV file into the canonical DataFrame shape.

    The CSV must contain a date column and at least a ``close`` column. Missing
    open/high/low values fall back to the close, and a missing volume column is
    filled with zeros so downstream code can rely on the columns existing.
    """
    path = Path(path)
    raw = pd.read_csv(path)
    raw.columns = [c.strip().lower() for c in raw.columns]

    date_col = next((c for c in ("date", "timestamp", "time") if c in raw.columns), None)
    if date_col is None:
        raise ValueError("CSV must contain a 'date', 'timestamp', or 'time' column")
    if "close" not in raw.columns:
        raise ValueError("CSV must contain a 'close' column")

    raw[date_col] = pd.to_datetime(raw[date_col])
    raw = raw.sort_values(date_col).set_index(date_col)
    raw.index.name = "date"

    for col in ("open", "high", "low"):
        if col not in raw.columns:
            raw[col] = raw["close"]
    if "volume" not in raw.columns:
        raw["volume"] = 0

    frame = raw[["open", "high", "low", "close", "volume"]].astype(float)
    frame.attrs["symbol"] = symbol or path.stem.upper()
    return frame
