import asyncio
import importlib
from config.config_settings import get_region

async def main():

    region = get_region().lower()
    module = importlib.import_module(f"regions.{region}.main_{region}")
    await module.main()

if __name__ == "__main__":
    asyncio.run(main())