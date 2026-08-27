"""Abstract broker interface shared by the simulated and live backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from .types import AccountInfo, OrderResult, OrderSide, Position, Tick


class Broker(ABC):
    """Minimal trading interface the agent depends on.

    The method surface intentionally mirrors the parts of the ``MetaTrader5``
    API the agent needs, so the live and simulated implementations are
    interchangeable.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Establish the connection / initialise state. Returns success."""

    @abstractmethod
    def shutdown(self) -> None:
        """Tear down the connection."""

    @abstractmethod
    def get_rates(self, symbol: str, count: int) -> pd.DataFrame:
        """Return the most recent ``count`` OHLC bars as a DataFrame.

        The frame is indexed by bar time with columns
        ``[open, high, low, close, volume]``.
        """

    @abstractmethod
    def get_tick(self, symbol: str) -> Tick:
        """Return the current tick (bid/ask) for ``symbol``."""

    @abstractmethod
    def account(self) -> AccountInfo:
        """Return current account balance/equity."""

    @abstractmethod
    def positions(self, symbol: str | None = None) -> list[Position]:
        """Return open positions, optionally filtered by symbol."""

    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        volume: float,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "",
    ) -> OrderResult:
        """Open a market position."""

    @abstractmethod
    def close_position(self, ticket: int, comment: str = "") -> OrderResult:
        """Close an open position by ticket."""
