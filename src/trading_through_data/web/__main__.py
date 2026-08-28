"""Run the dashboard with ``python -m trading_through_data.web``."""

from __future__ import annotations

import os

from .app import create_app


def main() -> None:
    app = create_app()
    host = os.environ.get("TTD_HOST", "0.0.0.0")
    port = int(os.environ.get("TTD_PORT", "5000"))
    debug = os.environ.get("TTD_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
