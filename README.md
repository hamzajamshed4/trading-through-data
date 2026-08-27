# trading-through-data

A small, self-contained **data-driven trading strategy backtester** with a web
dashboard. It generates (or loads) historical price data, runs a moving-average
crossover strategy, simulates the resulting equity curve, and reports
performance metrics — both from the command line and in the browser.

## Features

- **Data layer** (`trading_through_data.data`): deterministic synthetic price
  generation (geometric random walk, no network required) plus OHLC CSV loading.
- **Strategy** (`trading_through_data.strategy`): SMA-crossover signal generation
  with look-ahead protection.
- **Backtest engine** (`trading_through_data.backtest`): equity curve, Sharpe
  ratio, max drawdown, trade extraction, and transaction-cost modelling.
- **Web dashboard** (`trading_through_data.web`): a Flask app that renders the
  price/SMA chart, equity curve, metrics, and trade log.
- **CLI** (`ttd`): run a backtest and print a report.

## Requirements

- Python 3.10+ (developed and tested on 3.12)

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Usage

### Command line

```bash
# Synthetic data
ttd --days 365 --fast 20 --slow 50

# From a CSV of OHLC data
ttd --csv data/sample_prices.csv --symbol ACME --fast 3 --slow 5
```

### Web dashboard

```bash
python -m trading_through_data.web
# then open http://localhost:5000
```

Set `TTD_HOST`, `TTD_PORT`, or `TTD_DEBUG=1` to override the defaults.

### Tests

```bash
pytest
```

## Project layout

```
src/trading_through_data/
  data.py        # synthetic generation + CSV loading
  strategy.py    # SMA crossover signals
  backtest.py    # simulation + metrics
  plotting.py    # server-side matplotlib charts (base64 PNG)
  cli.py         # `ttd` command-line entry point
  web/           # Flask dashboard
tests/           # pytest suite
data/            # sample OHLC CSV
```

> Results are for demonstration only and are not investment advice.
