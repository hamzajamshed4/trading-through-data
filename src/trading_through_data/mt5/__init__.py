"""MetaTrader 5 connectivity layer.

This package abstracts the broker so the trading agent can run against either a
live MetaTrader 5 terminal (via the Windows-only ``MetaTrader5`` package) or a
fully offline :class:`SimulatedBroker` used for development, testing, and demos.
"""

from .base import Broker
from .simulated import SimulatedBroker
from .types import (
    AccountInfo,
    OrderResult,
    OrderSide,
    Position,
    Rate,
    Tick,
)

__all__ = [
    "Broker",
    "SimulatedBroker",
    "AccountInfo",
    "OrderResult",
    "OrderSide",
    "Position",
    "Rate",
    "Tick",
    "create_broker",
]


def create_broker(mode: str = "simulated", **kwargs) -> Broker:
    """Broker factory.

    ``mode="simulated"`` returns a :class:`SimulatedBroker`. ``mode="live"``
    returns a :class:`~trading_through_data.mt5.live.MetaTrader5Broker`, which
    requires the ``MetaTrader5`` package (Windows + a running MT5 terminal).
    """
    mode = mode.lower()
    if mode in ("sim", "simulated", "paper"):
        return SimulatedBroker(**kwargs)
    if mode in ("live", "mt5", "metatrader5"):
        from .live import MetaTrader5Broker

        return MetaTrader5Broker(**kwargs)
    raise ValueError(f"unknown broker mode: {mode!r}")
