import pandas as pd

from trading_through_data.backtest import run_backtest
from trading_through_data.data import generate_price_data


def test_backtest_result_structure():
    prices = generate_price_data(days=252, seed=5)
    result = run_backtest(prices, fast_window=20, slow_window=50)

    assert result.symbol == "SYNTH"
    assert len(result.equity_curve) == len(prices)
    for key in (
        "total_return",
        "buy_hold_return",
        "sharpe_ratio",
        "max_drawdown",
        "final_equity",
        "num_trades",
    ):
        assert key in result.metrics


def test_equity_starts_near_initial_capital():
    prices = generate_price_data(days=252, seed=5)
    result = run_backtest(prices, initial_capital=25_000.0)
    # No position is taken until the slow SMA is defined, so early equity is flat.
    assert abs(result.equity_curve.iloc[0] - 25_000.0) < 1e-6


def test_flat_market_has_no_trades():
    idx = pd.bdate_range("2023-01-01", periods=120)
    prices = pd.DataFrame({"close": [100.0] * 120}, index=idx)
    prices.attrs["symbol"] = "FLAT"
    result = run_backtest(prices, fast_window=5, slow_window=20)
    assert result.metrics["num_trades"] == 0
    assert abs(result.total_return) < 1e-9


def test_fees_reduce_returns():
    prices = generate_price_data(days=252, seed=11)
    no_fee = run_backtest(prices, fee_bps=0.0)
    with_fee = run_backtest(prices, fee_bps=25.0)
    if no_fee.metrics["num_trades"] > 0:
        assert with_fee.total_return < no_fee.total_return
