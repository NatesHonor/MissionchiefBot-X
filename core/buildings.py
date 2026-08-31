"""Building data collection shared by supported region adapters."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from utils.pretty_print import display_error, display_info

from .pages import ensure_page
from .regions import get_region_profile


async def gather_building_data_single(context, thread_id, url):
    try:
        from deep_translator import GoogleTranslator

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
            translated = GoogleTranslator(source="auto", target="en").translate(
                raw_key.replace("_", " ")
            )
            name = translated.strip().title().replace(" ", "_")
            building_data.setdefault(name, []).append(building_id)
        return building_data
    except Exception as error:
        display_error(f"[Building Thread {thread_id}] Error gathering building config: {error}")
        return {}


async def gather_building_data(contexts, thread_count, url, save_path=None, profile=None):
    profile = profile or get_region_profile()
    contexts = contexts if isinstance(contexts, list) else [contexts]
    if not contexts:
        return
    results = await asyncio.gather(
        *(
            gather_building_data_single(context, index + 1, url)
            for index, context in enumerate(contexts[:thread_count])
        )
    )
    merged = {}
    for result in results:
        for name, ids in result.items():
            values = merged.setdefault(name, [])
            values.extend(item for item in ids if item not in values)
    destination = Path(save_path or profile.building_file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as stream:
        json.dump(merged, stream, indent=2, ensure_ascii=False)
    display_info(f"Saved building config to {destination} with {len(merged)} categories.")


async def ensure_building_data(contexts, thread_count, url, profile=None):
    profile = profile or get_region_profile()
    if not profile.building_file.exists():
        await gather_building_data(contexts, thread_count, url, profile=profile)
