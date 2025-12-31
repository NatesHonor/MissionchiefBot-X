from utils.pretty_print import display_info, display_error
from utils.vehicle_options import get_vehicle_options
from .utils import format_distance, normalize_key
from data.cache import get_vehicle_data, lock_vehicle, is_vehicle_locked

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

async def click_vehicle(page, cb, vehicle_id, label, dist, mission_id):
    if await cb.is_checked():
        return False
    if not lock_vehicle(vehicle_id, mission_id):
        return False
    await page.evaluate(
        '(c) => { c.click(); c.dispatchEvent(new Event("change", { bubbles: true })); }',
        cb
    )
    display_info(f"Selected {label}({vehicle_id}) [{format_distance(dist)} away]")
    return True

async def select_vehicles(page, ids, needed, label, mission_id):
    checkboxes = await page.query_selector_all("input.vehicle_checkbox")
    checkbox_map = {await cb.get_attribute("value"): cb for cb in checkboxes}
    valid_ids = [vid for vid in ids if vid in checkbox_map and not is_vehicle_locked(vid)]
    if not valid_ids:
        return 0
    distance_map = await get_all_vehicle_distances(page, valid_ids)
    vehicles = [(vid, distance_map.get(vid, float('inf'))) for vid in valid_ids]
    vehicles.sort(key=lambda x: x[1])
    count = 0
    for vid, dist in vehicles:
        if count >= needed:
            break
        cb = checkbox_map[vid]
        if await click_vehicle(page, cb, vid, label, dist, mission_id):
            count += 1
    return count

async def find_vehicle_ids(name: str):
    VEHICLE_DATA = get_vehicle_data()
    norm = normalize_key(name)
    ids = []
    for k, v in VEHICLE_DATA.items():
        if normalize_key(k) == norm:
            ids.extend(v)
    for alt in get_vehicle_options(name):
        n = normalize_key(alt)
        for k, v in VEHICLE_DATA.items():
            if normalize_key(k) == n:
                ids.extend(v)
    ids = list(dict.fromkeys(ids))
    if not ids:
        display_error(f"No vehicles found for '{name}'")
    return ids
