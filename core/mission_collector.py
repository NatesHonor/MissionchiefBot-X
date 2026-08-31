"""Mission list collection shared by supported region adapters."""

from __future__ import annotations

import json

from utils.pretty_print import display_error, display_info
from utils.progress import ProgressBar

from .concurrency import split_mission_ids_among_threads
from .missionchief_api import fetch_mission_markers, refresh_mission_index
from .missionchief_api import fetch_mission_marker_records
from .mission_ignore import filter_ignored_mission_ids, load_mission_ignore_rules
from .pages import ensure_page
from .regions import get_region_profile
from .settings import get_settings
from .vehicle_state import get_vehicle_state
from utils.special_resources import collect_special_resources


def limit_mission_ids(mission_ids, maximum: int) -> tuple[list[str], int]:
    """Bound one collection pass while preserving input order.

    A zero maximum means unlimited.  Returning the omitted count lets the
    caller make the tradeoff visible instead of looking stalled.
    """

    ids = list(mission_ids)
    if maximum <= 0 or len(ids) <= maximum:
        return ids, 0
    return ids[:maximum], len(ids) - maximum


async def scan_event_resources(page, base_url: str, enabled: bool) -> int:
    """Scan event controls after the active mission list is identified."""

    if not enabled:
        return 0
    collected = await collect_special_resources(page, base_url)
    if collected:
        noun = "resource" if collected == 1 else "resources"
        display_info(f"Collected {collected} event {noun} during mission gathering.")
    else:
        display_info("Event-resource scan complete; no new resources found.")
    return collected


async def check_and_grab_missions(
    contexts,
    num_threads,
    url,
    profile=None,
    state=None,
    settings=None,
):
    profile = profile or get_region_profile()
    state = state or get_vehicle_state(profile)
    settings = settings or get_settings()
    contexts = contexts if isinstance(contexts, list) else [contexts]
    if not contexts:
        return
    profile.ensure_data_dir()
    try:
        page = await ensure_page(contexts[0])
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        mission_index = await refresh_mission_index(page, url, profile.mission_index_file)
        marker_records = await fetch_mission_marker_records(
            page,
            url,
            settings.include_alliance_missions,
        )
        ids = [record["id"] for record in marker_records]
        if not ids:
            ids = await fetch_mission_markers(
                page,
                url,
                settings.include_alliance_missions,
            )
        panels = await page.query_selector_all(".mission_panel_red")
        if not ids:
            for panel in panels:
                panel_id = await panel.get_attribute("id")
                if panel_id:
                    ids.append(panel_id.split("_")[-1])
        ids = list(dict.fromkeys(ids))
        await scan_event_resources(page, url, settings.auto_special_resources)
        cached_missions = {}
        if profile.mission_file.exists():
            try:
                cached_missions = json.loads(profile.mission_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                cached_missions = {}
        rules = load_mission_ignore_rules(profile)
        ids, ignored = filter_ignored_mission_ids(
            ids,
            rules,
            mission_index,
            {record["id"]: record for record in marker_records},
            cached_missions,
        )
        if ignored:
            display_info(f"Ignored {len(ignored)} configured mission(s) before detail scanning.")
        active_ids = set(ids)
        ids, omitted = limit_mission_ids(ids, getattr(settings, "max_missions", 500))
        if omitted:
            display_info(
                f"Mission collection capped at {len(ids)} active missions; "
                f"{omitted} additional alliance mission(s) will be picked up next pass."
            )
        for mission_id in cached_missions:
            if mission_id not in active_ids:
                state.free_for_mission(mission_id)
        if not ids:
            profile.mission_file.write_text("{}", encoding="utf-8")
            display_info("No missions found, stored an empty mission snapshot.")
            return
        display_info(f"Found {len(ids)} mission IDs.")
        progress = ProgressBar("Grabbing mission details", len(ids))
        progress.start()
        collection_succeeded = False
        try:
            data = await split_mission_ids_among_threads(
                ids,
                contexts,
                min(max(num_threads, 1), len(contexts), len(ids)),
                url,
                profile,
                state,
                progress,
            )
            collection_succeeded = True
        finally:
            progress.finish("complete" if collection_succeeded else "stopped")
        with profile.mission_file.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=4)
        display_info(f"Mission config collection complete. Stored mission config in {profile.mission_file}.")
    except Exception as error:
        display_error(f"Error gathering mission config: {error}")
