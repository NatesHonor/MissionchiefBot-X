"""Building data collection shared by supported region adapters."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from utils.pretty_print import display_error, display_info

from .data_store import document_has_records, save_document
from .browser import ensure_page
from .regions import get_region_profile


def _building_name(raw_key: str) -> str:
    """Return a readable name for a building image key.

    The key comes from the marker image file name (``building_fire.png`` ->
    ``fire``), which is English in every region, so it only needs tidying.
    It used to go through Google Translate, which hit Google's rate limit
    ("You made too many requests") and broke building collection.
    """

    return raw_key.replace("_", " ").strip().title().replace(" ", "_") or raw_key


async def gather_building_data_single(context, thread_id, url):
    try:
        display_info(f"[Building Thread {thread_id}] Starting building config grab")
        page = await ensure_page(context)
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        buttons = await page.query_selector_all("#btn-group-building-select a.building_selection")
        for button in buttons:
            classes = await button.get_attribute("class") or ""
            if "btn-danger" in classes:
                await button.click()
                await page.wait_for_load_state("networkidle")

        building_data = {}
        captions = await page.query_selector_all("div.building_list_caption")
        for caption in captions:
            image = await caption.query_selector("img.building_marker_image")
            if not image:
                continue
            source = await image.get_attribute("src")
            building_id = await image.get_attribute("building_id")
            if not source or not building_id:
                continue
            raw_key = source.rsplit("/", 1)[-1].replace(".png", "")
            if raw_key.startswith("building_"):
                raw_key = raw_key[len("building_") :]
            building_data.setdefault(_building_name(raw_key), []).append(building_id)
        return building_data
    except Exception as error:
        display_error(f"[Building Thread {thread_id}] Error gathering building config: {error}")
        return {}


async def gather_building_data(contexts, thread_count, url, save_path=None, profile=None) -> bool:
    """Gather the player's buildings and store them in SQLite.

    Returns True when buildings were stored. Nothing is written when every
    worker fails or finds nothing, so existing data is kept and the runner
    retries on its next loop.
    """

    profile = profile or get_region_profile()
    contexts = contexts if isinstance(contexts, list) else [contexts]
    if not contexts:
        display_error("Building collection skipped: no logged-in browser session is available.")
        return False
    display_info("Gathering buildings from the game...")
    results = await asyncio.gather(
        *(
            gather_building_data_single(context, index + 1, url)
            for index, context in enumerate(contexts[:thread_count])
        ),
        return_exceptions=True,
    )
    merged = {}
    for index, result in enumerate(results, start=1):
        if isinstance(result, BaseException):
            display_error(f"Building collection worker {index} failed: {type(result).__name__}: {result}")
            continue
        for name, ids in result.items():
            values = merged.setdefault(name, [])
            values.extend(item for item in ids if item not in values)
    if not merged:
        display_error("Building collection found no buildings. It will be retried on the next loop.")
        return False
    save_document(Path(save_path or profile.building_file), merged)
    total = sum(len(ids) for ids in merged.values())
    display_info(f"Stored {total} buildings in {len(merged)} categories in the database.")
    return True


async def ensure_building_data(contexts, thread_count, url, profile=None):
    profile = profile or get_region_profile()
    # Building IDs live in SQLite; gather them when nothing is stored yet.
    if not document_has_records(profile.building_file):
        await gather_building_data(contexts, thread_count, url, profile=profile)
