"""UK compatibility entrypoint; runtime orchestration lives in ``core``."""

from core.regions import get_region_profile
from core.runner import run_bot


async def main(config=None):
    await run_bot(profile=get_region_profile("uk"))
