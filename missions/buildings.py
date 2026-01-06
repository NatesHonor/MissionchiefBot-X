import os
import json
import asyncio
from utils.pretty_print import display_info, display_error
from deep_translator import GoogleTranslator

BUILDING_FILE = os.path.join("data", "building_data.json")

async def gather_building_data_single(context, thread_id, url):
    try:
        display_info(f"[Building Thread {thread_id}] Starting building data grab")
        page = context.pages[0]
        display_info(f"[Building Thread {thread_id}] Navigating to {url}")
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        display_info(f"[Building Thread {thread_id}] Page loaded")

        buttons = await page.query_selector_all("#btn-group-building-select a.building_selection")
        display_info(f"[Building Thread {thread_id}] Found {len(buttons)} building selection buttons")
        for idx, btn in enumerate(buttons):
            classes = await btn.get_attribute("class")
            display_info(f"[Building Thread {thread_id}] Button {idx+1} classes: {classes}")
            if "btn-danger" in classes:
                display_info(f"[Building Thread {thread_id}] Clicking danger button {idx+1}")
                await btn.click()
                await page.wait_for_load_state("networkidle")
                display_info(f"[Building Thread {thread_id}] Button {idx+1} clicked and page reloaded")

        captions = await page.query_selector_all("div.building_list_caption")
        display_info(f"[Building Thread {thread_id}] Found {len(captions)} building captions")
        building_data = {}
        for idx, cap in enumerate(captions):
            display_info(f"[Building Thread {thread_id}] Processing caption {idx+1}")
            img = await cap.query_selector("img.building_marker_image")
            if not img:
                display_info(f"[Building Thread {thread_id}] Caption {idx+1} has no image, skipping")
                continue
            src = await img.get_attribute("src")
            bid = await img.get_attribute("building_id")
            display_info(f"[Building Thread {thread_id}] Caption {idx+1} src={src}, id={bid}")
            if not src or not bid:
                display_info(f"[Building Thread {thread_id}] Caption {idx+1} missing src or id, skipping")
                continue

            raw_key = os.path.basename(src).replace(".png", "")
            if raw_key.startswith("building_"):
                raw_key = raw_key[len("building_"):]
            display_info(f"[Building Thread {thread_id}] Raw key={raw_key}")

            translated = GoogleTranslator(source="auto", target="en").translate(raw_key.replace("_", " "))
            display_info(f"[Building Thread {thread_id}] Translated key={translated}")

            name = translated.strip().title().replace(" ", "_")
            if name not in building_data:
                building_data[name] = []
                display_info(f"[Building Thread {thread_id}] Created new category {name}")
            building_data[name].append(bid)
            display_info(f"[Building Thread {thread_id}] Added building id {bid} to category {name}")

        display_info(f"[Building Thread {thread_id}] Finished with {len(building_data)} categories")
        return building_data
    except Exception as e:
        display_error(f"[Building Thread {thread_id}] Error gathering building data: {e}")
        return {}

async def gather_building_data(contexts, thread_count, url):
    display_info(f"[Building] Starting gather across {thread_count} threads")
    tasks = [gather_building_data_single(ctx, i+1, url) for i, ctx in enumerate(contexts[:thread_count])]
    results = await asyncio.gather(*tasks)
    display_info(f"[Building] Gather complete, merging results")

    merged = {}
    for idx, r in enumerate(results):
        display_info(f"[Building] Merging result from thread {idx+1} with {len(r)} categories")
        for k, v in r.items():
            merged.setdefault(k, []).extend(v)
            display_info(f"[Building] Category {k} now has {len(merged[k])} ids")

    os.makedirs("data", exist_ok=True)
    with open(BUILDING_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    display_info(f"[Building] Saved building data to {BUILDING_FILE} with {len(merged)} categories total")

async def ensure_building_data(contexts, thread_count, url):
    display_info("[Building] Ensuring building data file exists")
    if not os.path.exists(BUILDING_FILE):
        display_info("[Building] File missing, gathering data now")
        await gather_building_data(contexts, thread_count, url)
    else:
        display_info("[Building] File already exists, skipping gather")
