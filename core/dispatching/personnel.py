from __future__ import annotations

import re

from ..regions import get_region_profile
from ..settings import get_settings
from utils.personnel_options import get_personnel_options

from .utils import canonical_personnel, normalize_key
from .vehicles import find_vehicle_ids, select_vehicles


async def handle_personnel(page, data, missing, mission_id, profile=None, state=None, settings=None):
    profile = profile or get_region_profile()
    settings = settings or get_settings()
    skip_roles = {"technical rescuer", "usar", "sharpshooter"}
    for person in data.get("personnel", []):
        original = person["name"]
        needed = person["count"]
        if normalize_key(original) in skip_roles:
            continue
        stripped = re.sub(r"\([^)]*\)", "", original)
        mapping = {}
        for key in (canonical_personnel(original), normalize_key(original), normalize_key(stripped)):
            mapping = get_personnel_options(key)
            if mapping:
                break
        selected = 0
        for vehicle_type, per_vehicle in mapping.items():
            if selected >= needed:
                break
            ids = await find_vehicle_ids(vehicle_type, profile, state)
            needed_vehicles = (needed + per_vehicle - 1) // per_vehicle
            used = await select_vehicles(
                page,
                ids,
                needed_vehicles,
                vehicle_type,
                mission_id,
                profile,
                state,
            )
            selected += used * per_vehicle
            for requirement in data.get("vehicles", []):
                if any(
                    normalize_key(option) == normalize_key(vehicle_type)
                    for option in requirement.get("options", [])
                ):
                    requirement["count"] = max(0, requirement["count"] - used)
        if selected < needed and not settings.dispatch_incomplete:
            missing.append((original, needed - selected))
