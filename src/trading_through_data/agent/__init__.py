"""The AI trading agent for MetaTrader 5.

The agent observes market data from a :class:`~trading_through_data.mt5.Broker`,
extracts features, asks a :class:`~trading_through_data.agent.policy.Policy` for a
decision, sizes the trade with risk management, and executes it. It works
identically against the live MT5 broker and the simulated broker.
"""

from .policy import Decision, IndicatorPolicy, Policy, Signal
from .risk import RiskConfig
from .runner import AgentReport, TradingAgent

__all__ = [
    "Decision",
    "Signal",
    "Policy",
    "IndicatorPolicy",
    "RiskConfig",
    "TradingAgent",
    "AgentReport",
]
