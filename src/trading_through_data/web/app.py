"""Flask application factory and routes for the dashboard."""

from __future__ import annotations

from flask import Flask, render_template, request

from ..backtest import run_backtest
from ..data import generate_price_data
from ..plotting import render_equity_chart, render_price_chart


def _int_arg(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except (TypeError, ValueError):
        return default


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        symbol = request.args.get("symbol", "SYNTH") or "SYNTH"
        days = max(60, _int_arg("days", 365))
        fast = max(2, _int_arg("fast", 20))
        slow = max(fast + 1, _int_arg("slow", 50))
        seed = _int_arg("seed", 42)

        prices = generate_price_data(symbol=symbol, days=days, seed=seed)
        result = run_backtest(prices, fast_window=fast, slow_window=slow)

        return render_template(
            "index.html",
            symbol=symbol,
            params={"days": days, "fast": fast, "slow": slow, "seed": seed},
            metrics=result.metrics,
            trades=result.trades,
            price_chart=render_price_chart(result),
            equity_chart=render_equity_chart(result),
        )

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    return app
