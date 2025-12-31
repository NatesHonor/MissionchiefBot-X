import re
from data.config_settings import get_dispatch_incomplete
from utils.personnel_options import get_personnel_options
from .vehicles import find_vehicle_ids, select_vehicles
from .utils import normalize_key, canonical_personnel

async def handle_personnel(page, data, missing, mission_id):
    skip_roles = {"technical rescuer", "usar", "sharpshooter"}
    for person in data.get("personnel", []):
        original = person["name"]
        needed = person["count"]
        if normalize_key(original) in skip_roles:
            continue
        stripped = re.sub(r'\([^)]*\)', '', original)
        keys = [
            canonical_personnel(original),
            normalize_key(original),
            normalize_key(stripped)
        ]
        mapping = {}
        for k in keys:
            m = get_personnel_options(k)
            if m:
                mapping = m
                break
        selected = 0
        for vtype, per_vehicle in mapping.items():
            if selected >= needed:
                break
            ids = await find_vehicle_ids(vtype)
            needed_vehicles = (needed + per_vehicle - 1) // per_vehicle
            used = await select_vehicles(page, ids, needed_vehicles, vtype, mission_id)
            selected += used * per_vehicle
            for req in data.get("vehicles", []):
                if any(normalize_key(opt) == normalize_key(vtype) for opt in req.get("options", [])):
                    req["count"] = max(0, req["count"] - used)
            if selected >= needed:
                break
        if selected < needed and not get_dispatch_incomplete():
            missing.append((original, needed - selected))
