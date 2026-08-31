from __future__ import annotations

from utils.pretty_print import display_error, display_info

from ..regions import get_region_profile
from ..vehicle_state import get_vehicle_state
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
    checkboxes = await page.query_selector_all("input.vehicle_checkbox")
    checkbox_map = {await checkbox.get_attribute("value"): checkbox for checkbox in checkboxes}
    valid_ids = [
        vehicle_id
        for vehicle_id in ids
        if vehicle_id in checkbox_map and not state.is_locked(vehicle_id)
    ]
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


async def find_vehicle_ids(name: str, profile=None, state=None):
    profile = profile or get_region_profile()
    state = state or get_vehicle_state(profile)
    vehicle_data = state.get_data()
    normalized = normalize_key(name)
    ids = []
    names = [name, *profile.vehicle_options(name)]
    normalized_names = {normalize_key(item) for item in names if item}
    for vehicle_type, vehicle_ids in vehicle_data.items():
        normalized_type = normalize_key(vehicle_type)
        matches_name = normalized_type in normalized_names
        matches_variant = any(
            len(candidate) >= 4
            and (candidate in normalized_type or normalized_type in candidate)
            for candidate in normalized_names
        )
        if matches_name or matches_variant:
            ids.extend(str(vehicle_id) for vehicle_id in vehicle_ids)
    unique_ids = list(dict.fromkeys(ids))
    if not unique_ids:
        display_error(f"No vehicles found for '{name}'")
    return unique_ids
