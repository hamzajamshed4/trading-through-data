"""Backtest engine and performance metrics."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .strategy import sma_crossover_signals

TRADING_DAYS_PER_YEAR = 252


@dataclass
class BacktestResult:
    """Container for the outcome of a single backtest run."""

    symbol: str
    signals: pd.DataFrame
    equity_curve: pd.Series
    metrics: dict = field(default_factory=dict)
    trades: list = field(default_factory=list)

    @property
    def total_return(self) -> float:
        return self.metrics.get("total_return", 0.0)


def _max_drawdown(equity: pd.Series) -> float:
    """Return the maximum peak-to-trough drawdown as a negative fraction."""
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min())


def _extract_trades(index: pd.Index, position: pd.Series) -> list[dict]:
    """Turn a position series into a list of entry/exit trade records."""
    trades: list[dict] = []
    entry_idx = None
    for i, pos in enumerate(position.to_numpy()):
        if pos == 1 and entry_idx is None:
            entry_idx = i
        elif pos == 0 and entry_idx is not None:
            trades.append({"entry": index[entry_idx], "exit": index[i]})
            entry_idx = None
    if entry_idx is not None:
        trades.append({"entry": index[entry_idx], "exit": index[-1]})
    return trades


def run_backtest(
    prices: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    initial_capital: float = 10_000.0,
    fee_bps: float = 1.0,
) -> BacktestResult:
    """Run the SMA-crossover strategy over ``prices``.

    ``fee_bps`` charges a proportional transaction cost (in basis points) each
    time the position changes. Returns a fully populated :class:`BacktestResult`.
    """
    signals = sma_crossover_signals(prices, fast_window=fast_window, slow_window=slow_window)

    returns = signals["price"].pct_change().fillna(0.0)
    position = signals["position"]

    trade_changes = position.diff().abs().fillna(position.abs())
    fees = trade_changes * (fee_bps / 10_000.0)

    strategy_returns = position * returns - fees
    equity_curve = (1.0 + strategy_returns).cumprod() * initial_capital

    buy_hold_curve = (1.0 + returns).cumprod() * initial_capital

    total_return = float(equity_curve.iloc[-1] / initial_capital - 1.0)
    ann_factor = np.sqrt(TRADING_DAYS_PER_YEAR)
    vol = float(strategy_returns.std())
    sharpe = float(strategy_returns.mean() / vol * ann_factor) if vol > 0 else 0.0

    metrics = {
        "initial_capital": initial_capital,
        "final_equity": float(equity_curve.iloc[-1]),
        "total_return": total_return,
        "buy_hold_return": float(buy_hold_curve.iloc[-1] / initial_capital - 1.0),
        "annualized_return": float((1.0 + total_return) ** (TRADING_DAYS_PER_YEAR / max(len(prices), 1)) - 1.0),
        "sharpe_ratio": sharpe,
        "max_drawdown": _max_drawdown(equity_curve),
        "num_trades": int((trade_changes > 0).sum() // 2 + (trade_changes > 0).sum() % 2),
        "fast_window": fast_window,
        "slow_window": slow_window,
        "fee_bps": fee_bps,
    }

    trades = _extract_trades(prices.index, position)
    metrics["num_trades"] = len(trades)

    equity_curve.name = "equity"
    return BacktestResult(
        symbol=prices.attrs.get("symbol", "UNKNOWN"),
        signals=signals,
        equity_curve=equity_curve,
        metrics=metrics,
        trades=trades,
    )
