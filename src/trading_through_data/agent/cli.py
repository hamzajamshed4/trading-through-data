"""Command-line entry point for the MetaTrader 5 trading agent (``ttd-agent``)."""

from __future__ import annotations

import argparse
import os
import sys

from ..data import generate_price_data, load_price_data
from ..mt5 import create_broker
from .policy import IndicatorPolicy
from .risk import RiskConfig
from .runner import TradingAgent


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ttd-agent",
        description="Run the AI trading agent for MetaTrader 5 (simulated or live).",
    )
    p.add_argument("--mode", choices=["simulated", "live"], default="simulated",
                   help="Broker backend. 'live' requires MetaTrader5 + credentials.")
    p.add_argument("--symbol", default="SYNTH", help="Instrument symbol.")

    # Simulated-data options.
    p.add_argument("--csv", help="OHLC CSV to replay (simulated mode). Omit for synthetic data.")
    p.add_argument("--days", type=int, default=365, help="Synthetic history length.")
    p.add_argument("--seed", type=int, default=42, help="Synthetic data seed.")
    p.add_argument("--balance", type=float, default=10_000.0, help="Initial account balance.")

    # Strategy / risk knobs.
    p.add_argument("--fast", type=int, default=20, help="Fast SMA window.")
    p.add_argument("--slow", type=int, default=50, help="Slow SMA window.")
    p.add_argument("--risk", type=float, default=0.02, help="Risk fraction per trade.")
    p.add_argument("--atr-stop", type=float, default=2.0, help="Stop-loss in ATR multiples.")
    p.add_argument("--atr-take", type=float, default=3.0, help="Take-profit in ATR multiples.")

    # Live (MetaTrader5) connection options; env vars are the safer default.
    p.add_argument("--mt5-login", type=int, default=None, help="MT5 account login (or MT5_LOGIN).")
    p.add_argument("--mt5-server", default=None, help="MT5 server (or MT5_SERVER).")
    p.add_argument("--mt5-path", default=None, help="Path to terminal64.exe (or MT5_PATH).")
    p.add_argument("--timeframe", default="H1", help="Live timeframe, e.g. M15, H1, D1.")
    p.add_argument("--verbose", action="store_true", help="Print every bar's decision (simulated).")
    return p


def _run_simulated(args) -> int:
    if args.csv:
        prices = load_price_data(args.csv, symbol=args.symbol)
    else:
        prices = generate_price_data(symbol=args.symbol, days=args.days, seed=args.seed)

    broker = create_broker(
        "simulated", prices=prices, symbol=args.symbol, initial_balance=args.balance
    )
    risk = RiskConfig(risk_per_trade=args.risk, atr_stop_mult=args.atr_stop, atr_take_mult=args.atr_take)
    agent = TradingAgent(
        broker, args.symbol, policy=IndicatorPolicy(),
        risk=risk, fast_window=args.fast, slow_window=args.slow,
    )
    report = agent.run()

    if args.verbose:
        for d in report.decisions:
            if d["actions"]:
                print(f"{str(d['time'])[:10]}  {d['signal']:<5} score={d['score']:+.2f}  "
                      f"px={d['price']:.2f}  -> {', '.join(d['actions'])}")

    m = report.metrics
    print(f"\nAI MT5 agent report — {report.symbol} (simulated)")
    print("-" * 46)
    print(f"Bars processed     : {m['bars']}")
    print(f"Initial balance    : ${m['initial_balance']:,.2f}")
    print(f"Final equity       : ${m['final_equity']:,.2f}")
    print(f"Total return       : {m['total_return'] * 100:+.2f}%")
    print(f"Trades             : {m['num_trades']}")
    print(f"Win rate           : {m['win_rate'] * 100:.1f}%")
    pf = m["profit_factor"]
    print(f"Profit factor      : {pf if pf is not None else 'n/a'}")
    print(f"Max drawdown       : {m['max_drawdown'] * 100:.2f}%")
    return 0


def _run_live(args) -> int:
    login = args.mt5_login or (int(os.environ["MT5_LOGIN"]) if os.environ.get("MT5_LOGIN") else None)
    server = args.mt5_server or os.environ.get("MT5_SERVER")
    password = os.environ.get("MT5_PASSWORD")
    path = args.mt5_path or os.environ.get("MT5_PATH")

    try:
        broker = create_broker(
            "live", login=login, password=password, server=server,
            path=path, timeframe=args.timeframe,
        )
        broker.connect()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    agent = TradingAgent(broker, args.symbol, fast_window=args.fast, slow_window=args.slow,
                         risk=RiskConfig(risk_per_trade=args.risk, atr_stop_mult=args.atr_stop,
                                         atr_take_mult=args.atr_take))
    decision, features, actions = agent.run_once()
    print(f"AI MT5 agent — {args.symbol} (live, {args.timeframe})")
    print(f"price={features.close:.5f} rsi={features.rsi:.1f} atr={features.atr:.5f}")
    print(f"decision={decision.signal.value} score={decision.score:+.2f} "
          f"confidence={decision.confidence:.2f}")
    print(f"reason: {'; '.join(decision.reasons)}")
    print(f"actions: {actions or ['none']}")
    broker.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.mode == "live":
        return _run_live(args)
    return _run_simulated(args)


if __name__ == "__main__":
    sys.exit(main())
