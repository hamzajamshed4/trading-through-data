#!/usr/bin/env bash
# Idempotent environment bootstrap for trading-through-data.
# Installs the python venv system package (missing from the base image),
# creates a project virtualenv, and installs the package in editable mode.
set -euo pipefail

cd "$(dirname "$0")/.."

# python3-venv ships ensurepip, which the default image lacks. Installing it is
# idempotent; skip the slow apt path when the module is already importable.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y --no-install-recommends python3-venv
fi

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
