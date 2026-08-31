from __future__ import annotations

import asyncio
import json
import math
import re

from utils.pretty_print import display_error, display_info

from ..regions import get_region_profile
from ..localization import get_localized_terms
from ..settings import get_settings
from ..vehicle_state import get_vehicle_state
from .navigation import load_mission_page
from .personnel import handle_personnel
from .vehicles import find_vehicle_ids, select_vehicles


async def read_water_status(page, profile=None):
    profile = profile or get_region_profile()
    bar = await page.query_selector("div[class*='mission_water_bar_selected_']")
    if not bar:
        return 0, 0
    need_attribute = await bar.get_attribute("config-need_water")
    need_match = re.search(r"\d[\d\s.,]*", str(need_attribute or ""))
    need = int(re.sub(r"[^0-9]", "", need_match.group(0))) if need_match else 0
    text = await bar.inner_text()
    selected = 0
    for label in get_localized_terms(profile.language, "selected"):
        match = re.search(rf"{re.escape(label)}\s*[:\-]?\s*([\d\s.,]+)", text, re.IGNORECASE)
        if match:
            selected = int(re.sub(r"[^0-9]", "", match.group(1)))
            break
    if selected == 0:
        values = re.findall(r"\d[\d\s.,]*", text)
        if values:
            selected = int(re.sub(r"[^0-9]", "", values[0]))
    return selected, need


async def handle_water_requirement(page, missing, mission_id, profile=None, state=None, settings=None):
    profile = profile or get_region_profile()
    state = state or get_vehicle_state(profile)
    settings = settings or get_settings()
    selected, need = await read_water_status(page, profile)
    if need <= 0 or selected >= need:
        return
    tanker_ids = await find_vehicle_ids("water tanker", profile, state)
    firetruck_ids = await find_vehicle_ids("firetruck", profile, state)
    while True:
        selected, need = await read_water_status(page, profile)
        if need <= 0 or selected >= need:
            break
        used = 0
        if tanker_ids:
            used = await select_vehicles(page, tanker_ids, 1, "water tanker", mission_id, profile, state)
        if not used and firetruck_ids:
            used = await select_vehicles(page, firetruck_ids, 1, "firetruck", mission_id, profile, state)
        if not used:
            break
    selected, need = await read_water_status(page, profile)
    if selected < need and not settings.dispatch_incomplete:
        missing.append(("Water", need - selected))


async def navigate_and_dispatch(contexts, url, profile=None, state=None, settings=None):
    profile = profile or get_region_profile()
    state = state or get_vehicle_state(profile)
    settings = settings or get_settings()
    if not profile.mission_file.exists():
        return
    with profile.mission_file.open("r", encoding="utf-8") as stream:
        missions = list(json.load(stream).items())
    pages = [context.pages[0] for context in contexts if context.pages]
    if not pages or not missions:
        return
    chunk_size = math.ceil(len(missions) / len(pages))

    async def process_mission(page, mission_id, data, prefix):
        if not await load_mission_page(page, mission_id, data.get("mission_name", "Unknown"), url):
            return
        missing_vehicles_button = await page.query_selector("a.missing_vehicles_load.btn-warning")
        if missing_vehicles_button:
            await missing_vehicles_button.click()
            await page.wait_for_load_state("networkidle")
        missing = []
        await handle_personnel(page, data, missing, mission_id, profile, state, settings)
        for requirement in data.get("vehicles", []):
            needed = requirement.get("count", 0)
            if needed <= 0:
                continue
            used_total = 0
            for option in requirement.get("options", []):
                if used_total >= needed:
                    break
                ids = await find_vehicle_ids(option, profile, state)
                used = await select_vehicles(
                    page,
                    ids,
                    needed - used_total,
                    option,
                    mission_id,
                    profile,
                    state,
                )
                used_total += used
            if used_total < needed and not settings.dispatch_incomplete:
                missing.append(("/".join(requirement.get("options", [])), needed - used_total))

        crashed = data.get("crashed_cars", 0)
        if crashed > 0:
            flatbeds = await find_vehicle_ids("Flatbed Carrier", profile, state)
            used_flatbed = await select_vehicles(
                page, flatbeds, crashed, "Flatbed Carrier", mission_id, profile, state
            )
            covered = 2 * used_flatbed
            remaining = max(0, crashed - covered)
            if remaining > 0:
                wreckers = await find_vehicle_ids("wrecker", profile, state)
                used = await select_vehicles(
                    page,
                    wreckers,
                    remaining,
                    "Wrecker Police Wrecker Fire Wrecker",
                    mission_id,
                    profile,
                    state,
                )
                covered += used
                remaining = max(0, crashed - covered)
            if remaining > 0 and not settings.dispatch_incomplete:
                missing.append(("Tow Vehicles", remaining))

        await handle_water_requirement(page, missing, mission_id, profile, state, settings)
        if missing and not settings.dispatch_incomplete:
            state.free_for_mission(mission_id)
            display_error(
                f"{prefix} Mission {mission_id} missing requirements: "
                + ", ".join(f"{name}({count})" for name, count in missing)
            )
            return

        selector = (
            "a[class*='alert_next_alliance']"
            if settings.dispatch_type.lower() == "alliance"
            else "#alert_btn"
        )
        try:
            button = await page.wait_for_selector(selector, timeout=10000)
        except Exception:
            button = await page.query_selector("#alert_btn")
        if not button:
            display_error(f"{prefix} Dispatch button missing for {mission_id}")
            return
        try:
            await button.click()
            await page.wait_for_load_state("networkidle")
            display_info(f"{prefix} Dispatched mission {mission_id}")
        except Exception as error:
            display_error(f"{prefix} Dispatch click failed for {mission_id}: {error}")

    async def process_chunk(page, chunk, thread_id):
        prefix = f"[Mission Thread {thread_id}]"
        for mission_id, data in chunk:
            await process_mission(page, mission_id, data, prefix)

    tasks = []
    for index, page in enumerate(pages):
        chunk = missions[index * chunk_size : (index + 1) * chunk_size]
        if chunk:
            tasks.append(process_chunk(page, chunk, index + 1))
    await asyncio.gather(*tasks)
