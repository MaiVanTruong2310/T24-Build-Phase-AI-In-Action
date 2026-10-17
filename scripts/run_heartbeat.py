"""CLI launcher for autonomous heartbeat loops."""

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.heartbeat_worker import get_heartbeat_worker


async def main():
    parser = argparse.ArgumentParser(description="P-124 Heartbeat Maintenance Worker")
    parser.add_argument("--once", action="store_true", help="Execute single pulse and exit")
    parser.add_argument("--interval", type=int, default=60, help="Pulse interval in seconds")
    args = parser.parse_args()

    worker = get_heartbeat_worker()
    if args.once:
        res = await worker.pulse_once()
        print(f"Pulse result: {res}")
    else:
        await worker.run_forever(interval_seconds=args.interval)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
