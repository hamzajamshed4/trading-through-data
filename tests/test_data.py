import numpy as np
import pandas as pd
import pytest

from trading_through_data.data import generate_price_data, load_price_data


def test_generate_price_data_shape_and_columns():
    frame = generate_price_data(days=120, seed=7)
    assert len(frame) == 120
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]
    assert frame.attrs["symbol"] == "SYNTH"
    assert frame.index.is_monotonic_increasing


def test_generate_price_data_is_deterministic():
    a = generate_price_data(days=90, seed=123)
    b = generate_price_data(days=90, seed=123)
    pd.testing.assert_frame_equal(a, b)


def test_generate_price_data_high_low_bounds():
    frame = generate_price_data(days=200, seed=3)
    assert (frame["high"] >= frame["close"]).all()
    assert (frame["low"] <= frame["close"]).all()
    assert (frame["high"] >= frame["low"]).all()


def test_generate_price_data_rejects_bad_days():
    with pytest.raises(ValueError):
        generate_price_data(days=0)


def test_load_price_data_roundtrip(tmp_path):
    dates = pd.bdate_range("2022-01-03", periods=10)
    df = pd.DataFrame({"Date": dates, "Close": np.linspace(10, 20, 10)})
    csv = tmp_path / "acme.csv"
    df.to_csv(csv, index=False)

    loaded = load_price_data(csv)
    assert loaded.attrs["symbol"] == "ACME"
    assert list(loaded.columns) == ["open", "high", "low", "close", "volume"]
    # Missing OHLC columns fall back to close.
    assert (loaded["open"] == loaded["close"]).all()
    assert len(loaded) == 10


def test_load_price_data_requires_close(tmp_path):
    csv = tmp_path / "bad.csv"
    pd.DataFrame({"date": ["2022-01-01"], "price": [1.0]}).to_csv(csv, index=False)
    with pytest.raises(ValueError):
        load_price_data(csv)
