import pandas as pd
import pytest

from trading_through_data.data import generate_price_data
from trading_through_data.mt5 import SimulatedBroker
from trading_through_data.mt5.types import OrderSide


def _flat_prices(n=50, price=100.0):
    idx = pd.bdate_range("2023-01-01", periods=n)
    return pd.DataFrame(
        {"open": price, "high": price, "low": price, "close": price, "volume": 0.0},
        index=idx,
    )


def test_connect_and_rates_window():
    broker = SimulatedBroker(generate_price_data(days=100, seed=1))
    assert broker.connect() is True
    for _ in range(10):
        broker.step()
    rates = broker.get_rates("SYNTH", 5)
    assert len(rates) == 5
    assert list(rates.columns) == ["open", "high", "low", "close", "volume"]


def test_buy_profit_on_rising_market():
    idx = pd.bdate_range("2023-01-01", periods=5)
    prices = pd.DataFrame(
        {"open": [100, 101, 102, 103, 104], "high": [100, 101, 102, 103, 104],
         "low": [100, 101, 102, 103, 104], "close": [100, 101, 102, 103, 104], "volume": 0},
        index=idx,
    )
    broker = SimulatedBroker(prices, initial_balance=1000.0, spread_bps=0.0)
    broker.connect()
    res = broker.submit_order("SYNTH", OrderSide.BUY, volume=10)
    assert res.ok
    while broker.step():
        pass
    broker.close_position(res.ticket)
    # Bought at 100, closed at 104, 10 units -> +40.
    assert broker.balance == pytest.approx(1040.0, abs=1e-6)


def test_stop_loss_is_triggered():
    idx = pd.bdate_range("2023-01-01", periods=4)
    prices = pd.DataFrame(
        {"open": [100, 99, 95, 94], "high": [100, 99, 96, 95],
         "low": [100, 96, 90, 93], "close": [100, 98, 95, 94], "volume": 0},
        index=idx,
    )
    broker = SimulatedBroker(prices, initial_balance=1000.0, spread_bps=0.0)
    broker.connect()
    broker.submit_order("SYNTH", OrderSide.BUY, volume=1, sl=97.0, tp=110.0)
    broker.step()  # bar low 96 <= 97 -> stop hit
    assert broker.positions() == []
    assert len(broker.closed_positions) == 1
    assert broker.closed_positions[0]["reason"] == "stop_loss"


def test_account_equity_reflects_unrealized():
    prices = _flat_prices()
    broker = SimulatedBroker(prices, initial_balance=5000.0, spread_bps=0.0)
    broker.connect()
    broker.submit_order("SYNTH", OrderSide.BUY, volume=1)
    broker.step()
    acct = broker.account()
    assert acct.balance == pytest.approx(5000.0)
    assert acct.equity == pytest.approx(5000.0)  # flat market -> no PnL


def test_requires_enough_bars():
    with pytest.raises(ValueError):
        SimulatedBroker(_flat_prices(1))
