"""Shared data types for the MetaTrader 5 layer.

These mirror the concepts exposed by the ``MetaTrader5`` package (ticks, deals,
positions, account state) but as plain dataclasses so the simulated and live
brokers present an identical, typed interface to the agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    """Direction of a market order / position."""

    BUY = "buy"
    SELL = "sell"

    @property
    def sign(self) -> int:
        """+1 for long, -1 for short."""
        return 1 if self is OrderSide.BUY else -1

    @property
    def opposite(self) -> "OrderSide":
        return OrderSide.SELL if self is OrderSide.BUY else OrderSide.BUY


@dataclass(frozen=True)
class Rate:
    """A single OHLC bar."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class Tick:
    """A price quote at a point in time."""

    time: datetime
    bid: float
    ask: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0


@dataclass
class Position:
    """An open position tracked by the broker."""

    ticket: int
    symbol: str
    side: OrderSide
    volume: float
    entry_price: float
    entry_time: datetime
    sl: float | None = None
    tp: float | None = None
    profit: float = 0.0


@dataclass
class AccountInfo:
    """Snapshot of account balance and equity."""

    balance: float
    equity: float
    currency: str = "USD"
    leverage: int = 100


@dataclass
class OrderResult:
    """Outcome of an order request."""

    ok: bool
    ticket: int | None = None
    price: float | None = None
    comment: str = ""
