"""trading-through-data: a data-driven trading strategy backtester.

The package is organised around a small, testable pipeline:

* :mod:`trading_through_data.data` loads or synthesises historical price data.
* :mod:`trading_through_data.strategy` turns prices into trading signals.
* :mod:`trading_through_data.backtest` simulates the strategy and reports metrics.
* :mod:`trading_through_data.web` serves an interactive dashboard.
"""

from .backtest import BacktestResult, run_backtest
from .data import generate_price_data, load_price_data
from .strategy import sma_crossover_signals

__all__ = [
    "BacktestResult",
    "run_backtest",
    "generate_price_data",
    "load_price_data",
    "sma_crossover_signals",
    "TradingAgent",
    "IndicatorPolicy",
    "RiskConfig",
    "SimulatedBroker",
    "create_broker",
]


def __getattr__(name):  # lazy re-exports to keep import time light
    if name in ("TradingAgent", "IndicatorPolicy", "RiskConfig"):
        from . import agent

        return getattr(agent, name)
    if name in ("SimulatedBroker", "create_broker"):
        from . import mt5

        return getattr(mt5, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__version__ = "0.1.0"
