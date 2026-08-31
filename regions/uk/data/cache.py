"""Backward-compatible UK vehicle state imports."""

from core.regions import get_region_profile
from core.vehicle_state import get_vehicle_state

PROFILE = get_region_profile("uk")
_state = get_vehicle_state(PROFILE)


def get_vehicle_data():
    return _state.get_data()


def lock_vehicle(vehicle_id, mission_id):
    return _state.lock(str(vehicle_id), str(mission_id))


def is_vehicle_locked(vehicle_id):
    return _state.is_locked(str(vehicle_id))


def free_up_vehicles(mission_id):
    return _state.free_for_mission(str(mission_id))


def get_locked_vehicles(mission_id=None):
    return _state.locked(None if mission_id is None else str(mission_id))
