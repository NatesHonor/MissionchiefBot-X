import asyncio
import os
import sys
from pathlib import Path

from core.runner import run_bot


PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> int:
    """Run the bot from any working directory with a useful exit status."""

    os.chdir(PROJECT_ROOT)
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("MissionChief Bot stopped.")
    except Exception as error:
        print(f"MissionChief Bot could not start: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
