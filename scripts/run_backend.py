"""Cross-platform local launcher for the FastAPI backend.

Psycopg async requires a selector loop on Windows. Recent Uvicorn releases
choose a Proactor loop by default, so the loop factory must be supplied before
the application starts.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings  # noqa: E402


def compatible_loop_factory() -> asyncio.AbstractEventLoop:
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run the P-124 API")
    parser.add_argument("--host", default=settings.app_host)
    parser.add_argument("--port", type=int, default=settings.app_port)
    reload_default = settings.app_env == "development"
    parser.add_argument("--reload", action=argparse.BooleanOptionalAction, default=reload_default)
    args = parser.parse_args()
    uvicorn.run(
        "src.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        loop=compatible_loop_factory,
    )


if __name__ == "__main__":
    main()
