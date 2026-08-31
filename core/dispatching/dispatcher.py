from __future__ import annotations

import asyncio
import json
import math
import re

from utils.pretty_print import display_error, display_info

from ..regions import get_region_profile
from ..localization import get_localized_terms
from ..mission_requirements import (
    gather_requirements,
    normalize_cached_requirements,
    parse_requirement_count,
    resolve_personnel,
)
from ..mission_parser import resolve_vehicle_entry, resolve_vehicle_name
from ..vehicle_mapping import normalize_vehicle_name
from ..settings import get_settings
from ..vehicle_state import get_vehicle_state
from .navigation import load_mission_page
from .personnel import handle_personnel
from .vehicles import find_vehicle_ids, select_vehicles


def _requirement_key(options, profile=None):
    profile = profile or get_region_profile()
    return tuple(sorted(
        normalize_vehicle_name(resolve_vehicle_name(option, profile))
        for option in options
        if option
    ))


def _merge_vehicle_requirements(existing, current, profile=None):
    """Merge live expansion requirements into the cached mission snapshot."""

    profile = profile or get_region_profile()
    by_key = {
        _requirement_key(requirement.get("options", []), profile): requirement
        for requirement in existing
    }
    for requirement in current:
        if requirement.get("name"):
            incoming = resolve_vehicle_entry(
                requirement["name"],
                parse_requirement_count(requirement.get("count", 0)) or 0,
                profile,
            )
        else:
            incoming = {
                "options": requirement.get("options", []),
                "count": parse_requirement_count(requirement.get("count", 0)) or 0,
            }
        if not incoming["options"] or incoming["count"] <= 0:
            continue
        key = _requirement_key(incoming["options"], profile)
        saved = by_key.get(key)
        if saved is None:
            saved = {"options": list(incoming["options"]), "count": 0}
            existing.append(saved)
            by_key[key] = saved
        saved["count"] = max(
            parse_requirement_count(saved.get("count", 0)) or 0,
            incoming["count"],
        )


def _merge_personnel_requirements(existing, current, profile=None):
    profile = profile or get_region_profile()
    by_name = {
        normalize_vehicle_name(resolve_personnel(item.get("name", ""), profile)): item
        for item in existing
    }
    for item in current:
        name = resolve_personnel(item.get("name", ""), profile)
        count = parse_requirement_count(item.get("count", 0)) or 0
        if not name or count <= 0:
            continue
        key = normalize_vehicle_name(name)
        saved = by_name.get(key)
        if saved is None:
            saved = {"name": name, "count": 0}
            existing.append(saved)
            by_name[key] = saved
        saved["count"] = max(parse_requirement_count(saved.get("count", 0)) or 0, count)


async def _load_mission_expansions(page) -> bool:
    """Load every currently exposed expansion before dispatch planning."""

    selector = (
        "a.missing_vehicles_load.btn-warning, a.missing_vehicles_load, "
        "button.missing_vehicles_load"
    )
    clicked = set()
    expanded = False
    for _ in range(8):
        button = await page.query_selector(selector)
        if not button:
            break
        identity = await button.evaluate(
            """element => element.id || element.getAttribute('href') ||
            element.textContent || element.outerHTML"""
        )
        if identity in clicked:
            break
        clicked.add(identity)
        await button.click()
        await page.wait_for_load_state("networkidle")
        expanded = True
    return expanded


async def _merge_live_mission_requirements(page, data, profile):
    """Add requirements revealed by an expansion without dropping cached data."""

    help_button = await page.query_selector("#mission_help")
    if not help_button:
        return
    await help_button.click()
    await page.wait_for_selector("#iframe-inside-container", timeout=5000)
    current = await gather_requirements(page, profile)
    _merge_vehicle_requirements(data.setdefault("vehicles", []), current.get("vehicles", []), profile)
    _merge_vehicle_requirements(data.setdefault("liquid", []), current.get("liquid", []), profile)
    _merge_personnel_requirements(data.setdefault("personnel", []), current.get("personnel", []), profile)


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
        normalize_cached_requirements(data, profile)
        if not await load_mission_page(page, mission_id, data.get("mission_name", "Unknown"), url):
            return
        if await _load_mission_expansions(page):
            try:
                await _merge_live_mission_requirements(page, data, profile)
            except Exception as error:
                display_error(
                    f"{prefix} Could not refresh expanded requirements for {mission_id}: {error}"
                )
        missing = []
        await handle_personnel(page, data, missing, mission_id, profile, state, settings)
        for requirement in data.get("vehicles", []):
            needed = parse_requirement_count(requirement.get("count", 0))
            if needed is None or needed <= 0:
                continue
            requirement["count"] = needed
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
