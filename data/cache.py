import json, os

_vehicle_file = os.path.join(os.path.dirname(__file__), "vehicle_data.json")
VEHICLE_DATA = None
_LOCKED_VEHICLES = {}

def get_vehicle_data():
    global VEHICLE_DATA
    if VEHICLE_DATA is None:
        if not os.path.exists(_vehicle_file):
            return {}
        with open(_vehicle_file, "r", encoding="utf-8") as f:
            VEHICLE_DATA = json.load(f)
    return VEHICLE_DATA

def lock_vehicle(vehicle_id, mission_id):
    if vehicle_id in _LOCKED_VEHICLES:
        return False
    _LOCKED_VEHICLES[vehicle_id] = mission_id
    return True

def is_vehicle_locked(vehicle_id):
    return vehicle_id in _LOCKED_VEHICLES

def free_up_vehicles(mission_id):
    global _LOCKED_VEHICLES
    _LOCKED_VEHICLES = {vid: mid for vid, mid in _LOCKED_VEHICLES.items() if mid != mission_id}

def get_locked_vehicles(mission_id=None):
    if mission_id is None:
        return dict(_LOCKED_VEHICLES)
    return {vid: mid for vid, mid in _LOCKED_VEHICLES.items() if mid == mission_id}
