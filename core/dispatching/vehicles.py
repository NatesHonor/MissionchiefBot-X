from __future__ import annotations

import asyncio

from utils.pretty_print import display_error, display_info

from ..regions import get_region_profile
from ..vehicle_state import get_vehicle_state
from ..vehicle_mapping import is_decorated_vehicle_name, vehicle_name_variants
from .utils import format_distance, normalize_key


async def get_all_vehicle_distances(page, ids):
    script = """
    (ids) => {
        const result = {};
        for (const id of ids) {
            const el = document.querySelector(`#vehicle_sort_${id}`);
            if (el) {
                const val = el.getAttribute('sortvalue');
                result[id] = val ? parseInt(val) : Infinity;
            } else {
                result[id] = Infinity;
            }
        }
        return result;
    }
    """
    return await page.evaluate(script, ids)


async def click_vehicle(page, checkbox, vehicle_id, label, distance, mission_id, state=None, profile=None):
    state = state or get_vehicle_state(profile or get_region_profile())
    if await checkbox.is_checked() or not state.lock(str(vehicle_id), str(mission_id)):
        return False
    try:
        await page.evaluate(
            "(c) => { c.click(); c.dispatchEvent(new Event('change', { bubbles: true })); }",
            checkbox,
        )
    except Exception:
        state.unlock(str(vehicle_id), str(mission_id))
        return False
    display_info(f"Selected {label}({vehicle_id}) [{format_distance(distance)} away]")
    return True


async def select_vehicles(
    page,
    ids,
    needed,
    label,
    mission_id,
    profile=None,
    state=None,
):
    state = state or get_vehicle_state(profile or get_region_profile())
    if needed <= 0:
        return 0
    checkbox_map = {}
    valid_ids = []
    for attempt in range(3):
        checkboxes = await page.query_selector_all("input.vehicle_checkbox")
        checkbox_map = {
            await checkbox.get_attribute("value"): checkbox for checkbox in checkboxes
        }
        valid_ids = [
            vehicle_id
            for vehicle_id in ids
            if vehicle_id in checkbox_map and not state.is_locked(vehicle_id)
        ]
        if valid_ids:
            break
        if attempt < 2:
            try:
                await page.wait_for_selector("input.vehicle_checkbox", timeout=1500)
            except Exception:
                pass
            await asyncio.sleep(0.25 * (attempt + 1))
    if not valid_ids:
        return 0
    distance_map = await get_all_vehicle_distances(page, valid_ids)
    vehicles = [(vehicle_id, distance_map.get(vehicle_id, float("inf"))) for vehicle_id in valid_ids]
    vehicles.sort(key=lambda item: item[1])
    selected = 0
    for vehicle_id, distance in vehicles:
        if selected >= needed:
            break
        if await click_vehicle(
            page,
            checkbox_map[vehicle_id],
            vehicle_id,
            label,
            distance,
            mission_id,
            state,
            profile,
        ):
            selected += 1
    return selected


async def find_vehicle_ids(name: str, profile=None, state=None, exact=False, quiet=False):
    profile = profile or get_region_profile()
    state = state or get_vehicle_state(profile)
    vehicle_data = state.get_data()
    ids = []
    names = [name]
    if not exact:
        names.extend(profile.vehicle_options(name))
    normalized_names = {
        variant
        for item in names
        if item
        for variant in vehicle_name_variants(item)
    }
    for vehicle_type, vehicle_ids in vehicle_data.items():
        normalized_type = normalize_key(vehicle_type)
        matches_name = bool(normalized_names & vehicle_name_variants(vehicle_type))
        # Inventory captions sometimes append a model/crew qualifier in
        # parentheses.  Permit that explicit decoration, but do not fall
        # back to arbitrary substring matches between unrelated vehicle types.
        decorated_match = (not exact) and is_decorated_vehicle_name(
            normalized_names, vehicle_type
        )
        if matches_name or decorated_match:
            ids.extend(str(vehicle_id) for vehicle_id in vehicle_ids)
    unique_ids = list(dict.fromkeys(ids))
    if not unique_ids and not quiet:
        display_error(f"No vehicles found for '{name}'")
    return unique_ids
