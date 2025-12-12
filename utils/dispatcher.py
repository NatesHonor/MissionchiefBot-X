import asyncio
import json
import re
from data.config_settings import get_dispatch_type, get_dispatch_incomplete
from utils.personnel_options import get_personnel_options
from utils.pretty_print import display_info, display_error
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
        return int(val)
    except:
        return float('inf')

async def click_vehicle(page, vehicle_id, label):
    cb = await page.query_selector(f'input.vehicle_checkbox[value="{vehicle_id}"]')
    if cb:
        dist = await get_vehicle_distance(page, vehicle_id)
        await page.evaluate('(c)=>c.scrollIntoView()', cb)
        await page.evaluate('(c)=>{c.click();c.dispatchEvent(new Event("change",{bubbles:true}))}', cb)
        display_info(f"Selected {label}({vehicle_id}) [{format_distance(dist)} away]")
        return True
    return False

async def select_vehicles(page, ids, needed, label):
    vehicles_with_distance = []
    for vid in ids:
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
    return re.sub(r'\s+', ' ', s.strip().lower())

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
        if not await load_mission_page(page, mission_id, data.get("mission_name","Unknown")):
            continue
        btn = await page.query_selector('a.missing_vehicles_load.btn-warning')
        if btn:
            await btn.click()
            await page.wait_for_load_state('networkidle')
        missing = []
        for req in data.get("vehicles", []):
            name, count = req["name"], req["count"]
            if "SWAT Personnel" in name:
                needed_armoured = count // 6
                used = await select_vehicles(page, await find_vehicle_ids("SWAT Armoured Vehicle"), needed_armoured, "SWAT Armoured Vehicle")
                if used < needed_armoured:
                    await select_vehicles(page, await find_vehicle_ids("SWAT SUV"), count - used, "SWAT SUV")
                if used < needed_armoured and not get_dispatch_incomplete():
                    missing.append((name, needed_armoured - used))
                continue
            ids = await find_vehicle_ids(name)
            used = await select_vehicles(page, ids, count, name)
            if used < count and not get_dispatch_incomplete():
                missing.append((name, count - used))
        for person in data.get("required_personnel", []):
            p_name = person["name"].lower()
            needed = person["count"]
            mapping = get_personnel_options(p_name)
            selected = 0
            for vtype, per_vehicle in mapping.items():
                ids = await find_vehicle_ids(vtype)
                for _ in range(await select_vehicles(page, ids, 9999, vtype)):
                    selected += per_vehicle
                    if selected >= needed:
                        break
                if selected >= needed:
                    break
            if selected < needed and not get_dispatch_incomplete():
                missing.append((p_name, needed - selected))
        crashed = data.get("crashed_cars", 0)
        if crashed > 0:
            flatbeds = await find_vehicle_ids("Flatbed Carrier")
            used_flatbed = await select_vehicles(page, flatbeds, min(1, crashed), "Flatbed Carrier")
            covered = 2 * used_flatbed
            remaining = crashed - covered
            if remaining > 0:
                used_wreckers = await select_vehicles(page, await find_vehicle_ids("Wrecker"), remaining, "Wrecker")
                covered += used_wreckers
                remaining = crashed - covered
            if remaining > 0 and not get_dispatch_incomplete():
                missing.append(("Tow Vehicles", remaining))
        if missing and not get_dispatch_incomplete():
            display_error(f"❌ Mission {mission_id} missing requirements: " + ", ".join([f"{m[0]}({m[1]})" for m in missing]))
            continue
        d = get_dispatch_type() or "default"
        selector = 'a[class*="alert_next_alliance"]' if d.lower()=="alliance" else '#alert_btn'
        btn = await page.query_selector(selector) or await page.query_selector('#alert_btn')
        if btn:
            await btn.click()
            display_info(f"Dispatched mission {mission_id}")
        else:
            display_error(f"Dispatch button missing for {mission_id}")
