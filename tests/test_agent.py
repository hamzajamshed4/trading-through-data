import pandas as pd

from trading_through_data.agent import IndicatorPolicy, RiskConfig, TradingAgent
from trading_through_data.data import generate_price_data
from trading_through_data.mt5 import SimulatedBroker


def _agent(prices, **kw):
    broker = SimulatedBroker(prices=prices, symbol="SYNTH", initial_balance=10_000.0)
    return TradingAgent(broker, "SYNTH", policy=IndicatorPolicy(), risk=RiskConfig(), **kw)


def test_agent_run_produces_report():
    prices = generate_price_data(days=300, seed=3)
    report = _agent(prices, fast_window=10, slow_window=30).run()

    assert report.symbol == "SYNTH"
    assert report.metrics["bars"] == len(report.decisions)
    assert len(report.equity_curve) == len(report.decisions)
    for key in ("initial_balance", "final_equity", "total_return", "num_trades", "max_drawdown"):
        assert key in report.metrics


def test_agent_trades_on_trending_data():
    prices = generate_price_data(days=400, seed=9)
    report = _agent(prices, fast_window=10, slow_window=30).run()
    # A 400-bar synthetic series should trigger at least one entry/exit.
    assert report.metrics["num_trades"] >= 1
    # Every closed trade has a realized profit value.
    assert all("profit" in t for t in report.trades)


def test_no_position_before_warmup():
    slow = 50
    prices = generate_price_data(days=300, seed=3)
    report = _agent(prices, fast_window=20, slow_window=slow).run()
    # No actions may occur before the slow SMA is defined (first ready bar is
    # at index slow - 1), so everything strictly before that must be inactive.
    for d in report.decisions[: slow - 1]:
        assert not d["actions"]


def test_agent_flat_market_no_trades():
    idx = pd.bdate_range("2023-01-01", periods=200)
    prices = pd.DataFrame(
        {"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 0.0}, index=idx
    )
    report = _agent(prices, fast_window=10, slow_window=30).run()
    assert report.metrics["num_trades"] == 0


def test_run_once_requires_no_stepping():
    prices = generate_price_data(days=300, seed=3)
    broker = SimulatedBroker(prices=prices, symbol="SYNTH")
    broker.connect()
    for _ in range(120):
        broker.step()
    agent = TradingAgent(broker, "SYNTH", fast_window=10, slow_window=30)
    decision, features, actions = agent.run_once()
    assert decision.signal.value in ("buy", "sell", "hold", "close")
    assert isinstance(actions, list)
