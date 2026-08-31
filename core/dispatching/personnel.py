from __future__ import annotations

import re

from ..regions import get_region_profile
from ..mission_requirements import parse_requirement_count
from ..settings import get_settings
from utils.personnel_options import get_personnel_options

from .utils import canonical_personnel, normalize_key
from .vehicles import find_vehicle_ids, select_vehicles


def plan_personnel_vehicles(needed, candidates):
    """Choose the smallest vehicle combination that carries the personnel.

    ``candidates`` contains ``(vehicle_type, capacity, available_count)``.
    Exact inventory matching is important here because a SWAT armoured vehicle
    and a SWAT SUV have different personnel capacities.
    """

    try:
        needed = int(needed)
    except (TypeError, ValueError):
        return []
    if needed <= 0:
        return []

    states = {0: (0, ())}
    usable_candidates = []
    for vehicle_type, capacity, available in candidates:
        try:
            capacity = int(capacity)
            available = max(0, int(available))
        except (TypeError, ValueError):
            continue
        if capacity <= 0 or available <= 0:
            continue
        usable_candidates.append((vehicle_type, capacity, available))

    for vehicle_type, capacity, available in usable_candidates:
        next_states = {}
        for covered, (vehicle_count, counts) in states.items():
            for quantity in range(available + 1):
                total_covered = covered + (quantity * capacity)
                candidate = (vehicle_count + quantity, counts + (quantity,))
                previous = next_states.get(total_covered)
                if previous is None or candidate < previous:
                    next_states[total_covered] = candidate
        states = next_states

    feasible = [
        (covered, vehicle_count, counts)
        for covered, (vehicle_count, counts) in states.items()
        if covered >= needed
    ]
    if not feasible:
        return []

    _, _, counts = min(
        feasible,
        key=lambda item: (item[1], item[0] - needed, item[2]),
    )
    return [
        (usable_candidates[index][0], quantity)
        for index, quantity in enumerate(counts)
        if quantity
    ]


async def handle_personnel(page, data, missing, mission_id, profile=None, state=None, settings=None):
    profile = profile or get_region_profile()
    settings = settings or get_settings()
    skip_roles = {"technical rescuer", "usar", "sharpshooter"}
    for person in data.get("personnel", []):
        original = person["name"]
        needed = parse_requirement_count(person.get("count", 0))
        if needed is None or needed <= 0:
            continue
        if normalize_key(original) in skip_roles:
            continue
        stripped = re.sub(r"\([^)]*\)", "", original)
        mapping = {}
        for key in (canonical_personnel(original), normalize_key(original), normalize_key(stripped)):
            mapping = get_personnel_options(key)
            if mapping:
                break
        candidate_data = {}
        exact_lookup = normalize_key(original) == "swat personnel"
        for vehicle_type, per_vehicle in mapping.items():
            lookup_options = {"exact": True, "quiet": True} if exact_lookup else {}
            ids = await find_vehicle_ids(vehicle_type, profile, state, **lookup_options)
            if ids:
                candidate_data[vehicle_type] = (per_vehicle, ids)

        plan = plan_personnel_vehicles(
            needed,
            [
                (vehicle_type, per_vehicle, len(ids))
                for vehicle_type, (per_vehicle, ids) in candidate_data.items()
            ],
        )
        selected = 0
        for vehicle_type, needed_vehicles in plan:
            per_vehicle, ids = candidate_data[vehicle_type]
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
                    remaining = parse_requirement_count(requirement.get("count", 0))
                    if remaining is not None:
                        requirement["count"] = max(0, remaining - used)
        if selected < needed and not settings.dispatch_incomplete:
            missing.append((original, needed - selected))
