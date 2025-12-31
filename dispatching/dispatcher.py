import asyncio
import json
import math
import re
from data.config_settings import get_dispatch_type, get_dispatch_incomplete
from utils.pretty_print import display_info, display_error
from .vehicles import find_vehicle_ids, select_vehicles
from .personnel import handle_personnel
from .navigation import load_mission_page

async def read_water_status(page):
    bar = await page.query_selector('div[class*="mission_water_bar_selected_"]')
    if not bar:
        return 0, 0
    need_attr = await bar.get_attribute("data-need_water")
    need = int(need_attr) if need_attr and need_attr.isdigit() else 0
    txt = await bar.inner_text()
    m = re.search(r"Selected:\s*([\d,]+)\s*gal", txt)
    selected = int(m.group(1).replace(",", "")) if m else 0
    return selected, need

async def handle_water_requirement(page, missing, mission_id):
    selected, need = await read_water_status(page)
    if need <= 0 or selected >= need:
        return
    tanker_ids = await find_vehicle_ids("water tanker")
    firetruck_ids = await find_vehicle_ids("firetruck")
    while True:
        selected, need = await read_water_status(page)
        if need <= 0 or selected >= need:
            break
        progressed = False
        if tanker_ids:
            used = await select_vehicles(page, tanker_ids, 1, "water tanker", mission_id)
            if used > 0:
                progressed = True
                continue
        if firetruck_ids and not progressed:
            used = await select_vehicles(page, firetruck_ids, 1, "firetruck", mission_id)
            if used > 0:
                progressed = True
                continue
        if not progressed:
            break
    selected, need = await read_water_status(page)
    if selected < need and not get_dispatch_incomplete():
        missing.append(("Water", need - selected))

async def navigate_and_dispatch(contexts):
    with open('data/mission_data.json') as f:
        missions = list(json.load(f).items())
    pages = [ctx.pages[0] for ctx in contexts if ctx.pages]
    if not pages:
        return
    chunk_size = math.ceil(len(missions) / len(pages))

    async def process_chunk(page, chunk, thread_id):
        prefix = f"[Mission Thread {thread_id}]"

        async def process_mission(mission_id, data):
            if not await load_mission_page(page, mission_id, data.get("mission_name", "Unknown")):
                return
            btn = await page.query_selector('a.missing_vehicles_load.btn-warning')
            if btn:
                await btn.click()
                await page.wait_for_load_state('networkidle')
            missing = []
            await handle_personnel(page, data, missing, mission_id)
            for req in data.get("vehicles", []):
                needed = req.get("count", 0)
                if needed <= 0:
                    continue
                used_total = 0
                for opt in req.get("options", []):
                    if used_total >= needed:
                        break
                    ids = await find_vehicle_ids(opt)
                    used = await select_vehicles(page, ids, needed - used_total, opt, mission_id)
                    used_total += used
                if used_total < needed and not get_dispatch_incomplete():
                    missing.append(("/".join(req.get("options", [])), needed - used_total))
            crashed = data.get("crashed_cars", 0)
            if crashed > 0:
                flatbeds = await find_vehicle_ids("Flatbed Carrier")
                used_flatbed = await select_vehicles(page, flatbeds, crashed, "Flatbed Carrier", mission_id)
                covered = 2 * used_flatbed
                remaining = max(0, crashed - covered)
                if remaining > 0:
                    wreckers = []
                    for w in ["Wrecker", "Police Wrecker", "Fire Wrecker"]:
                        wreckers.extend(await find_vehicle_ids(w))
                    used = await select_vehicles(page, wreckers, remaining, "Wrecker Police Wrecker Fire Wrecker", mission_id)
                    covered += used
                    remaining = max(0, crashed - covered)
                if remaining > 0 and not get_dispatch_incomplete():
                    missing.append(("Tow Vehicles", remaining))
            await handle_water_requirement(page, missing, mission_id)
            if missing and not get_dispatch_incomplete():
                display_error(
                    f"{prefix} ❌ Mission {mission_id} missing requirements: "
                    + ", ".join([f"{m[0]}({m[1]})" for m in missing])
                )
                return
            d = get_dispatch_type() or "default"
            selector = 'a[class*="alert_next_alliance"]' if d.lower() == "alliance" else '#alert_btn'
            btn = await page.query_selector(selector) or await page.query_selector('#alert_btn')
            if btn:
                await btn.click()
                display_info(f"{prefix} Dispatched mission {mission_id}")
            else:
                display_error(f"{prefix} Dispatch button missing for {mission_id}")

        tasks = [process_mission(mission_id, data) for mission_id, data in chunk]
        await asyncio.gather(*tasks)

    tasks = []
    for i, page in enumerate(pages):
        chunk = missions[i*chunk_size:(i+1)*chunk_size]
        if chunk:
            tasks.append(process_chunk(page, chunk, i+1))
    await asyncio.gather(*tasks)
