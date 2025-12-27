import json, os

_vehicle_file = os.path.join(os.path.dirname(__file__), "vehicle_data.json")
VEHICLE_DATA = None

def get_vehicle_data():
    global VEHICLE_DATA
    if VEHICLE_DATA is None:
        if not os.path.exists(_vehicle_file):
            return {}
        with open(_vehicle_file, "r", encoding="utf-8") as f:
            VEHICLE_DATA = json.load(f)
    return VEHICLE_DATA
