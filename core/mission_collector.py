"""Mission list collection shared by supported region adapters."""

from __future__ import annotations

import json

from utils.pretty_print import display_error, display_info
from utils.progress import ProgressBar

from .concurrency import split_mission_ids_among_threads
from .missionchief_api import fetch_mission_markers, refresh_mission_index
from .pages import ensure_page
from .regions import get_region_profile
from .settings import get_settings
from .vehicle_state import get_vehicle_state
from utils.special_resources import collect_special_resources


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
        await refresh_mission_index(page, url, profile.mission_index_file)
        if settings.auto_special_resources:
            collected = await collect_special_resources(page, url)
            if collected:
                await page.goto(url)
                await page.wait_for_load_state("networkidle")
        ids = await fetch_mission_markers(page, url)
        panels = await page.query_selector_all(".mission_panel_red")
        if not ids:
            for panel in panels:
                panel_id = await panel.get_attribute("id")
                if panel_id:
                    ids.append(panel_id.split("_")[-1])
        ids = list(dict.fromkeys(ids))
        if not ids:
            if profile.mission_file.exists():
                try:
                    previous = json.loads(profile.mission_file.read_text(encoding="utf-8"))
                    for mission_id in previous:
                        state.free_for_mission(mission_id)
                except (OSError, json.JSONDecodeError, TypeError):
                    pass
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
