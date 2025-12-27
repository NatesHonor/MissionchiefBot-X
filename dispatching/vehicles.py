import asyncio, json
from utils.pretty_print import display_info, display_error, display_warning
from utils.vehicle_options import get_vehicle_options
from .utils import format_distance, normalize_key

async def get_vehicle_distance(page, vehicle_id):
    el = await page.query_selector(f'#vehicle_sort_{vehicle_id}')
    if not el:
        return float('inf')
    val = await el.get_attribute('sortvalue')
    try:
        val = int(val)
        if val < 0 or val > 86400 * 365:
            return float('inf')
        return val
    except:
        return float('inf')

async def click_vehicle(page, cb, vehicle_id, label):
    if await cb.is_checked():
        display_warning(f"Skipped {label}({vehicle_id}) already selected")
        return False
    dist = await get_vehicle_distance(page, vehicle_id)
    await page.evaluate(
        '(c) => { c.click(); c.dispatchEvent(new Event("change", { bubbles: true })); }',
        cb
    )
    display_info(f"Selected {label}({vehicle_id}) [{format_distance(dist)} away]")
    return True

async def select_vehicles(page, ids, needed, label):
    checkboxes = await page.query_selector_all("input.vehicle_checkbox")
    checkbox_map = {await cb.get_attribute("value"): cb for cb in checkboxes}
    tasks = [get_vehicle_distance(page, vid) for vid in ids if vid in checkbox_map]
    distances = await asyncio.gather(*tasks)
    vehicles = list(zip([vid for vid in ids if vid in checkbox_map], distances))
    vehicles.sort(key=lambda x: x[1])
    count = 0
    for vid, _ in vehicles:
        if count >= needed:
            break
        cb = checkbox_map[vid]
        if await click_vehicle(page, cb, vid, label):
            count += 1
    return count

async def find_vehicle_ids(name):
    with open('data/vehicle_data.json') as f:
        vehicle_data = json.load(f)
    norm = normalize_key(name)
    ids = []
    for k, v in vehicle_data.items():
        if normalize_key(k) == norm:
            ids.extend(v)
    for alt in get_vehicle_options(name):
        n = normalize_key(alt)
        for k, v in vehicle_data.items():
            if normalize_key(k) == n:
                ids.extend(v)
    if not ids:
        display_error(f"No vehicles found for '{name}'")
    return ids
