import asyncio
import json

from utils.pretty_print import display_info, display_error


async def gather_vehicle_data(browsers, num_threads):
    first_browser = browsers[0]
    try:
        page = first_browser.contexts[0].pages[0]
        await page.goto("https://www.missionchief.com/leitstellenansicht")
        await page.wait_for_selector('.list-group')

        vehicle_links = await page.query_selector_all('.list-group a[href^="/vehicles/"]')
        vehicle_ids = [await link.get_attribute('href') for link in vehicle_links]
        vehicle_ids = [href.split('/')[-1] for href in vehicle_ids]

        display_info(f"Found {len(vehicle_ids)} vehicle IDs.")

        vehicle_data = await split_vehicle_ids_among_threads(vehicle_ids, browsers, num_threads)

        with open('data/vehicle_data.json', 'w') as outfile:
            json.dump(vehicle_data, outfile, indent=4)

        display_info(f"Vehicle data collection complete. Stored vehicle data in vehicle_data.json.")

    except Exception as e:
        display_error(f"Error gathering vehicle data: {e}")

async def gather_vehicle_info(vehicle_ids, browser, thread_id):
    vehicle_data = {}
    page = browser.contexts[0].pages[0]

    for index, vehicle_id in enumerate(vehicle_ids):
        try:
            display_info(f"Thread {thread_id}: Grabbing vehicles {index+1}/{len(vehicle_ids)}")
            await page.goto(f"https://www.missionchief.com/vehicles/{vehicle_id}")
            vehicle_type_element = await page.query_selector('#vehicle-attr-type a')
            vehicle_type = await vehicle_type_element.inner_text()

            if vehicle_type not in vehicle_data:
                vehicle_data[vehicle_type] = []

            vehicle_data[vehicle_type].append(vehicle_id)
        except Exception as e:
            display_error(f"Error processing vehicle ID {vehicle_id}: {e}")

    return vehicle_data

async def split_vehicle_ids_among_threads(vehicle_ids, browsers, num_threads):
    vehicle_data = {}
    thread_vehicle_ids = [vehicle_ids[i::num_threads] for i in range(num_threads)]

    tasks = [gather_vehicle_info(thread_vehicle_ids[i], browsers[i], i+1) for i in range(num_threads)]
    results = await asyncio.gather(*tasks)

    for result in results:
        for vehicle_type, ids in result.items():
            if vehicle_type not in vehicle_data:
                vehicle_data[vehicle_type] = []
            vehicle_data[vehicle_type].extend(ids)

    return vehicle_data
