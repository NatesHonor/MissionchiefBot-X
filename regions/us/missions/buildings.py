"""Backward-compatible US building collector imports."""

from core.buildings import (
    ensure_building_data as _ensure_building_data,
    gather_building_data as _gather_building_data,
    gather_building_data_single,
)
from core.regions import get_region_profile

PROFILE = get_region_profile("us")
BUILDING_FILE = str(PROFILE.building_file)


async def gather_building_data(contexts, thread_count, url, save_path=None):
    return await _gather_building_data(
        contexts, thread_count, url, save_path=save_path, profile=PROFILE
    )


async def ensure_building_data(contexts, thread_count, url):
    return await _ensure_building_data(contexts, thread_count, url, profile=PROFILE)
