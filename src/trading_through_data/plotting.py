"""Server-side chart rendering.

Charts are rendered with a non-interactive Matplotlib backend and returned as
base64-encoded PNGs so they can be embedded directly in HTML without any
client-side JavaScript or CDN dependency.
"""

from __future__ import annotations

import base64
import io

import matplotlib

matplotlib.use("Agg")  # headless backend; must be set before pyplot import.

import matplotlib.pyplot as plt  # noqa: E402

from .backtest import BacktestResult  # noqa: E402


def _fig_to_base64(fig) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("ascii")


def render_price_chart(result: BacktestResult) -> str:
    """Render price with SMAs and long-position shading as a base64 PNG."""
    signals = result.signals
    fig, ax = plt.subplots(figsize=(10, 4.2))

    ax.plot(signals.index, signals["price"], label="Price", color="#1f2937", linewidth=1.3)
    ax.plot(signals.index, signals["sma_fast"], label="SMA fast", color="#2563eb", linewidth=1.1)
    ax.plot(signals.index, signals["sma_slow"], label="SMA slow", color="#f59e0b", linewidth=1.1)

    ax.fill_between(
        signals.index,
        signals["price"].min(),
        signals["price"].max(),
        where=signals["position"] == 1,
        color="#22c55e",
        alpha=0.10,
        label="Long",
    )

    ax.set_title(f"{result.symbol} — price & SMA crossover signals")
    ax.set_ylabel("Price")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.25)
    return _fig_to_base64(fig)


def render_equity_chart(result: BacktestResult) -> str:
    """Render the strategy equity curve as a base64 PNG."""
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.plot(result.equity_curve.index, result.equity_curve.values, color="#16a34a", linewidth=1.4)
    ax.axhline(result.metrics["initial_capital"], color="#9ca3af", linestyle="--", linewidth=1.0)
    ax.set_title("Strategy equity curve")
    ax.set_ylabel("Equity ($)")
    ax.grid(True, alpha=0.25)
    return _fig_to_base64(fig)
