"""Mission list collection shared by supported region adapters."""

from __future__ import annotations

import json

from utils.pretty_print import display_error, display_info

from .concurrency import split_mission_ids_among_threads
from .pages import ensure_page
from .regions import get_region_profile
from .vehicle_state import get_vehicle_state


async def check_and_grab_missions(contexts, num_threads, url, profile=None, state=None):
    profile = profile or get_region_profile()
    state = state or get_vehicle_state(profile)
    contexts = contexts if isinstance(contexts, list) else [contexts]
    if not contexts:
        return
    profile.ensure_data_dir()
    try:
        page = await ensure_page(contexts[0])
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        panels = await page.query_selector_all(".mission_panel_red")
        if not panels:
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
        ids = []
        for panel in panels:
            panel_id = await panel.get_attribute("id")
            if panel_id:
                ids.append(panel_id.split("_")[-1])
        display_info(f"Found {len(ids)} mission IDs.")
        data = await split_mission_ids_among_threads(
            ids,
            contexts,
            min(max(num_threads, 1), len(contexts), len(ids)),
            url,
            profile,
            state,
        )
        with profile.mission_file.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=4)
        display_info(f"Mission config collection complete. Stored mission config in {profile.mission_file}.")
    except Exception as error:
        display_error(f"Error gathering mission config: {error}")
