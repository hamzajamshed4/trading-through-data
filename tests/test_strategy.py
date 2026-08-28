import pandas as pd
import pytest

from trading_through_data.data import generate_price_data
from trading_through_data.strategy import sma_crossover_signals


def test_signals_columns_and_alignment():
    prices = generate_price_data(days=150, seed=1)
    signals = sma_crossover_signals(prices, fast_window=10, slow_window=30)
    assert list(signals.columns) == ["price", "sma_fast", "sma_slow", "position"]
    assert len(signals) == len(prices)
    assert set(signals["position"].unique()).issubset({0, 1})


def test_position_is_flat_before_slow_window():
    prices = generate_price_data(days=150, seed=1)
    signals = sma_crossover_signals(prices, fast_window=10, slow_window=30)
    # Position is shifted by one bar, so the first slow_window bars are flat.
    assert (signals["position"].iloc[:30] == 0).all()


def test_uptrend_produces_long_position():
    # Strictly increasing prices -> fast SMA above slow SMA -> long.
    idx = pd.bdate_range("2023-01-01", periods=120)
    prices = pd.DataFrame({"close": range(1, 121)}, index=idx)
    signals = sma_crossover_signals(prices, fast_window=5, slow_window=20)
    assert signals["position"].iloc[-1] == 1


def test_invalid_windows_raise():
    prices = generate_price_data(days=60, seed=1)
    with pytest.raises(ValueError):
        sma_crossover_signals(prices, fast_window=50, slow_window=20)
    with pytest.raises(ValueError):
        sma_crossover_signals(prices, fast_window=0, slow_window=20)
