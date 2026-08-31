from core.mission_requirements import gather_requirements as _gather_requirements
from core.mission_requirements import resolve_personnel as _resolve_personnel
from core.regions import get_region_profile

PROFILE = get_region_profile("us")


def resolve_personnel(name: str) -> str:
    return _resolve_personnel(name, PROFILE)


async def gather_requirements(page):
    return await _gather_requirements(page, PROFILE)
