"""Backward-compatible US mission collector imports."""

from core.mission_collector import check_and_grab_missions as _check_and_grab_missions
from core.regions import get_region_profile
from core.vehicle_state import get_vehicle_state

PROFILE = get_region_profile("us")
MISSION_FILE = PROFILE.mission_file


async def check_and_grab_missions(contexts, num_threads, url):
    return await _check_and_grab_missions(
        contexts,
        num_threads,
        url,
        PROFILE,
        get_vehicle_state(PROFILE),
    )
