import asyncio
import json
from pathlib import Path

from utils.pretty_print import display_info, display_error

from core.missionchief_api import fetch_vehicle_records, vehicle_inventory_from_records


async def gather_vehicle_data(contexts, num_threads, url, save_path):
    if not isinstance(contexts, list):
        contexts = [contexts]
    if not contexts:
        return
    if not contexts[0].pages:
        await contexts[0].new_page()

    try:
        page = contexts[0].pages[0]
        api_records = await fetch_vehicle_records(page, url)
        api_vehicle_data = vehicle_inventory_from_records(api_records)
        if api_vehicle_data:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with save_path.open("w", encoding="utf-8") as outfile:
                json.dump(api_vehicle_data, outfile, indent=4, ensure_ascii=False)
            display_info(
                f"Vehicle API collection complete. Stored {len(api_records)} vehicles in {save_path}."
            )
            return
        await page.goto(url + "leitstellenansicht", wait_until="domcontentloaded")
        await page.wait_for_selector(".list-group")

        vehicle_links = await page.query_selector_all('.list-group a[href^="/vehicles/"]')
        vehicle_ids = [await link.get_attribute("href") for link in vehicle_links]
        vehicle_ids = [href.split("/")[-1] for href in vehicle_ids if href]

        display_info(f"Found {len(vehicle_ids)} vehicle IDs.")

        threads = min(num_threads, len(contexts)) if num_threads else len(contexts)
        vehicle_data = await split_vehicle_ids_among_threads(vehicle_ids, contexts, threads, url)

        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with save_path.open("w", encoding="utf-8") as outfile:
            json.dump(vehicle_data, outfile, indent=4)

        display_info(f"Vehicle config collection complete. Stored vehicle config in {save_path}.")
    except Exception as e:
        display_error(f"Error gathering vehicle config: {e}")


async def gather_vehicle_info(vehicle_ids, context, thread_id, url):
    vehicle_data = {}

    if not context.pages:
        await context.new_page()
    page = context.pages[0]

    for index, vehicle_id in enumerate(vehicle_ids):
        try:
            display_info(f"Thread {thread_id}: Grabbing vehicles {index + 1}/{len(vehicle_ids)}")
            await page.goto(url + f"vehicles/{vehicle_id}", wait_until="domcontentloaded")
            await page.wait_for_selector("#vehicle-attr-type a", timeout=5000)
            vehicle_type_element = await page.query_selector("#vehicle-attr-type a")
            if not vehicle_type_element:
                continue
            vehicle_type = (await vehicle_type_element.inner_text()).strip()
            if vehicle_type not in vehicle_data:
                vehicle_data[vehicle_type] = []
            vehicle_data[vehicle_type].append(vehicle_id)
        except Exception as e:
            display_error(f"Error processing vehicle ID {vehicle_id}: {e}")

    return vehicle_data


async def split_vehicle_ids_among_threads(vehicle_ids, contexts, num_threads, url):
    if not vehicle_ids or not contexts:
        return {}
    threads = min(num_threads, len(contexts)) if num_threads else len(contexts)
    partitions = [vehicle_ids[i::threads] for i in range(threads)]

    for ctx in contexts[:threads]:
        if not ctx.pages:
            await ctx.new_page()

    tasks = [
        gather_vehicle_info(partitions[i], contexts[i], i + 1, url)
        for i in range(threads)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged = {}
    for index, result in enumerate(results, start=1):
        if isinstance(result, BaseException):
            display_error(
                f"Vehicle collection worker {index} failed: "
                f"{type(result).__name__}: {result}"
            )
            continue
        for vehicle_type, ids in result.items():
            if vehicle_type not in merged:
                merged[vehicle_type] = []
            merged[vehicle_type].extend(ids)

    return merged
