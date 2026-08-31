import asyncio

from core.runner import run_bot


async def main():
    await run_bot()

if __name__ == "__main__":
    asyncio.run(main())
