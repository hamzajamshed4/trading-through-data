"""Command-line interface for running backtests."""

from __future__ import annotations

import argparse
import sys

from .backtest import run_backtest
from .data import generate_price_data, load_price_data


def _format_pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ttd",
        description="Backtest a simple moving-average crossover strategy.",
    )
    parser.add_argument("--csv", help="Path to an OHLC CSV file. Omit to use synthetic data.")
    parser.add_argument("--symbol", default="SYNTH", help="Instrument symbol label.")
    parser.add_argument("--days", type=int, default=365, help="Synthetic history length in trading days.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for synthetic data.")
    parser.add_argument("--fast", type=int, default=20, help="Fast SMA window.")
    parser.add_argument("--slow", type=int, default=50, help="Slow SMA window.")
    parser.add_argument("--capital", type=float, default=10_000.0, help="Initial capital.")
    parser.add_argument("--fee-bps", type=float, default=1.0, help="Per-trade fee in basis points.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.csv:
        prices = load_price_data(args.csv, symbol=args.symbol)
    else:
        prices = generate_price_data(symbol=args.symbol, days=args.days, seed=args.seed)

    result = run_backtest(
        prices,
        fast_window=args.fast,
        slow_window=args.slow,
        initial_capital=args.capital,
        fee_bps=args.fee_bps,
    )
    m = result.metrics

    print(f"Backtest report for {result.symbol}")
    print("-" * 40)
    print(f"Bars analysed      : {len(prices)}")
    print(f"SMA windows        : {m['fast_window']} / {m['slow_window']}")
    print(f"Trades executed    : {m['num_trades']}")
    print(f"Initial capital    : ${m['initial_capital']:,.2f}")
    print(f"Final equity       : ${m['final_equity']:,.2f}")
    print(f"Total return       : {_format_pct(m['total_return'])}")
    print(f"Buy & hold return  : {_format_pct(m['buy_hold_return'])}")
    print(f"Annualized return  : {_format_pct(m['annualized_return'])}")
    print(f"Sharpe ratio       : {m['sharpe_ratio']:.2f}")
    print(f"Max drawdown       : {_format_pct(m['max_drawdown'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
