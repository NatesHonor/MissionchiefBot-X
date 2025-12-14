import asyncio
import json
import re
from data.config_settings import get_dispatch_type, get_dispatch_incomplete
from utils.personnel_options import get_personnel_options
from utils.pretty_print import display_info, display_error, display_warning
from utils.vehicle_options import get_vehicle_options

def format_distance(seconds):
    if seconds == float('inf'):
        return "unknown"
    if seconds < 60:
        return f"{seconds} sec"
    if seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins} min {secs} sec"
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    return f"{hrs} hr {mins} min"

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

async def click_vehicle(page, vehicle_id, label):
    cb = await page.query_selector(f'input.vehicle_checkbox[value="{vehicle_id}"]')
    if not cb:
        display_warning(f"Skipped {label}({vehicle_id}) checkbox not found")
        return False
    checked = await cb.is_checked()
    if checked:
        display_warning(f"Skipped {label}({vehicle_id}) already selected")
        return False
    dist = await get_vehicle_distance(page, vehicle_id)
    await page.evaluate('(c)=>c.scrollIntoView()', cb)
    await page.evaluate('(c)=>{c.click();c.dispatchEvent(new Event("change",{bubbles:true}))}', cb)
    display_info(f"Selected {label}({vehicle_id}) [{format_distance(dist)} away]")
    return True

async def select_vehicles(page, ids, needed, label):
    vehicles_with_distance = []
    seen = set()
    for vid in ids:
        if vid in seen:
            continue
        seen.add(vid)
        cb = await page.query_selector(f'input.vehicle_checkbox[value="{vid}"]')
        if not cb:
            continue
        dist = await get_vehicle_distance(page, vid)
        vehicles_with_distance.append((vid, dist))
    vehicles_with_distance.sort(key=lambda x: x[1])
    count = 0
    for vid, _ in vehicles_with_distance:
        if count >= needed:
            break
        if await click_vehicle(page, vid, label):
            count += 1
    return count

async def load_mission_page(page, mission_id, name):
    url = f"https://www.missionchief.com/missions/{mission_id}"
    for attempt in range(2):
        try:
            display_info(f"Navigating: {url} (Attempt {attempt+1})")
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_selector('#missionH1', timeout=5000)
            display_info(f"Loaded mission {name} ({mission_id})")
            return True
        except:
            if attempt == 1:
                display_error(f"❌ Failed loading mission {mission_id}, skipping.")
                return False
            await asyncio.sleep(2)
    return False

def normalize_key(s: str) -> str:
    return re.sub(r'\s+', ' ', s.strip().casefold())

def canonical_personnel(s: str) -> str:
    # strip parentheses content
    s = re.sub(r'\([^)]*\)', '', s)
    s = s.casefold()
    # remove non-alphanumeric
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    # collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    synonyms = {
        'swat personnel': 'swat personnel',
        'swat': 'swat personnel',
        's w a t personnel': 'swat personnel'
    }
    return synonyms.get(s, s)

async def find_vehicle_ids(name):
    with open('data/vehicle_data.json') as f:
        vehicle_data = json.load(f)
    norm_name = normalize_key(name)
    ids = []
    for k, v in vehicle_data.items():
        if normalize_key(k) == norm_name:
            ids.extend(v)
    for alt in get_vehicle_options(name):
        norm_alt = normalize_key(alt)
        for k, v in vehicle_data.items():
            if normalize_key(k) == norm_alt:
                ids.extend(v)
    if not ids:
        display_error(f"No vehicles found for '{name}'")
    return ids

async def navigate_and_dispatch(browsers):
    with open('data/mission_data.json') as f:
        missions = json.load(f)
    page = browsers[0].contexts[0].pages[0]
    for mission_id, data in missions.items():
        if not await load_mission_page(page, mission_id, data.get("mission_name", "Unknown")):
            continue
        btn = await page.query_selector('a.missing_vehicles_load.btn-warning')
        if btn:
            display_info("Found load missing vehicles")
            await btn.click()
            await page.wait_for_load_state('networkidle')
        missing = []
        for req in data.get("vehicles", []):
            name, count = req["name"], req["count"]
            ids = await find_vehicle_ids(name)
            used = await select_vehicles(page, ids, count, name)
            if used < count and not get_dispatch_incomplete():
                missing.append((name, count - used))
        for person in data.get("personnel", []):
            original_name = person["name"]
            needed = person["count"]
            stripped = re.sub(r'\([^)]*\)', '', original_name)
            keys = [
                canonical_personnel(original_name),
                normalize_key(original_name),
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
                ids = await find_vehicle_ids(vtype)
                needed_vehicles = (needed + per_vehicle - 1) // per_vehicle
                used = await select_vehicles(page, ids, needed_vehicles, vtype)
                selected += used * per_vehicle
                if selected >= needed:
                    break
            if selected < needed and not get_dispatch_incomplete():
                missing.append((original_name, needed - selected))
        crashed = data.get("crashed_cars", 0)
        if crashed > 0:
            flatbeds = await find_vehicle_ids("Flatbed Carrier")
            used_flatbed = await select_vehicles(page, flatbeds, crashed, "Flatbed Carrier")
            covered = 2 * used_flatbed
            remaining = max(0, crashed - covered)
            if remaining > 0:
                used_wreckers = await select_vehicles(page, await find_vehicle_ids("Wrecker"), remaining, "Wrecker")
                covered += used_wreckers
                remaining = max(0, crashed - covered)
            if remaining > 0 and not get_dispatch_incomplete():
                missing.append(("Tow Vehicles", remaining))
        if missing and not get_dispatch_incomplete():
            display_error(f"❌ Mission {mission_id} missing requirements: " + ", ".join([f"{m[0]}({m[1]})" for m in missing]))
            continue
        d = get_dispatch_type() or "default"
        selector = 'a[class*="alert_next_alliance"]' if d.lower() == "alliance" else '#alert_btn'
        btn = await page.query_selector(selector) or await page.query_selector('#alert_btn')
        if btn:
            await btn.click()
            display_info(f"Dispatched mission {mission_id}")
        else:
            display_error(f"Dispatch button missing for {mission_id}")
