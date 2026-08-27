# trading-through-data

An **AI trading agent for MetaTrader 5**, plus the data tooling and backtester
behind it. The agent observes market data, extracts technical features, decides
with an explainable policy, sizes trades with risk management, and executes
orders — against either a live MetaTrader 5 terminal or a fully offline
simulated broker for development and demos.

## Features

### AI MetaTrader 5 agent
- **Broker layer** (`trading_through_data.mt5`): a `Broker` abstraction with a
  `SimulatedBroker` (offline paper-trading engine that replays OHLC bars, fills
  orders with spread, and settles stop-loss / take-profit) and a live
  `MetaTrader5Broker` backed by the Windows-only `MetaTrader5` package.
- **Agent** (`trading_through_data.agent`): indicator features (SMA, RSI, ATR,
  momentum), an explainable `IndicatorPolicy` (trend + momentum + RSI blend),
  ATR-based position sizing / SL / TP (`RiskConfig`), and a `TradingAgent`
  observe → decide → size → execute loop that produces a run report.
- **Agent CLI** (`ttd-agent`): run the agent in `--mode simulated` (default) or
  `--mode live`.
- **Agent dashboard** (`/agent`): equity curve, decision log, and closed trades.

### Data & backtest tooling
- **Data layer** (`trading_through_data.data`): deterministic synthetic price
  generation (geometric random walk, no network required) plus OHLC CSV loading.
- **Strategy** (`trading_through_data.strategy`): SMA-crossover signals.
- **Backtest engine** (`trading_through_data.backtest`): equity curve, Sharpe,
  max drawdown, trade extraction, and transaction-cost modelling.
- **Web dashboard** (`trading_through_data.web`): Flask app (backtest + agent).
- **Backtest CLI** (`ttd`): run a backtest and print a report.

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

### AI MT5 agent (command line)

```bash
# Simulated broker (offline) on synthetic data
ttd-agent --days 400 --seed 9 --fast 10 --slow 30 --risk 0.02 --verbose

# Simulated broker replaying your own OHLC CSV
ttd-agent --csv data/sample_prices.csv --symbol ACME --fast 3 --slow 5
```

#### Live MetaTrader 5 mode

Live trading requires the Windows-only `MetaTrader5` package, a running MT5
terminal, and a broker account. It cannot run on Linux/macOS.

```bash
pip install "trading-through-data[mt5]"      # on Windows
# credentials via environment variables (preferred):
#   MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH (optional)
ttd-agent --mode live --symbol EURUSD --timeframe H1
```

`--mode live` performs one observe → decide → execute cycle and prints the
decision; schedule it (cron / Task Scheduler / a loop) to run it continuously.

### Backtest (command line)

```bash
ttd --days 365 --fast 20 --slow 50                                 # synthetic
ttd --csv data/sample_prices.csv --symbol ACME --fast 3 --slow 5   # from CSV
```

### Web dashboard

```bash
python -m trading_through_data.web
# backtest dashboard: http://localhost:5000
# AI agent dashboard: http://localhost:5000/agent
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
  cli.py         # `ttd` backtest CLI
  mt5/           # MetaTrader 5 broker layer
    base.py        #   Broker interface
    simulated.py   #   offline paper-trading broker
    live.py        #   live MetaTrader5 adapter (optional [mt5] extra)
    types.py       #   orders / positions / ticks / account
  agent/         # the AI trading agent
    features.py    #   SMA / RSI / ATR / momentum
    policy.py      #   explainable decision policy
    risk.py        #   ATR-based sizing + SL/TP
    runner.py      #   observe -> decide -> size -> execute loop
    cli.py         #   `ttd-agent` CLI
  web/           # Flask dashboard (backtest + /agent)
tests/           # pytest suite
data/            # sample OHLC CSV
```

## Simulated vs live

The `SimulatedBroker` and `MetaTrader5Broker` implement the same `Broker`
interface, so the identical `TradingAgent` runs against both. Develop, test, and
demo against the simulated broker anywhere; switch to `--mode live` on Windows
with MT5 for real connectivity. No application code changes are required.

> Results are for demonstration only and are not investment advice.
