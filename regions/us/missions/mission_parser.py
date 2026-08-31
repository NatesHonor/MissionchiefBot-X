"""Backward-compatible US mission parser imports."""

from core.mission_parser import (
    free_up_vehicles as _free_up_vehicles,
    gather_mission_info as _gather_mission_info,
    load_vehicle_aliases as _load_vehicle_aliases,
    resolve_vehicle_entry as _resolve_vehicle_entry,
    resolve_vehicle_name as _resolve_vehicle_name,
)
from core.regions import get_region_profile
from core.vehicle_state import get_vehicle_state

PROFILE = get_region_profile("us")
DATA_DIR = PROFILE.data_dir
CACHE_DIR = DATA_DIR


def free_up_vehicles(mission_id):
    return _free_up_vehicles(mission_id, PROFILE, get_vehicle_state(PROFILE))


def load_vehicle_aliases():
    return _load_vehicle_aliases(PROFILE)


def resolve_vehicle_name(name: str) -> str:
    return _resolve_vehicle_name(name, PROFILE)


def resolve_vehicle_entry(raw_name: str, count: int):
    return _resolve_vehicle_entry(raw_name, count, PROFILE)


async def gather_mission_info(ids, context, tid, url):
    return await _gather_mission_info(
        ids, context, tid, url, PROFILE, get_vehicle_state(PROFILE)
    )
