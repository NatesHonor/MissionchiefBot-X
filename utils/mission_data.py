import asyncio
import json
import os

from utils.pretty_print import display_info, display_error

async def check_and_grab_missions(browsers, num_threads):
    first_browser = browsers[0]
    try:
        if os.path.exists('data/mission_data.json'):
            os.remove('data/mission_data.json')
        page = first_browser.contexts[0].pages[0]
        await page.goto("https://www.missionchief.com")
        await page.wait_for_selector('.mission_panel_red')

        mission_panels = await page.query_selector_all('.mission_panel_red')
        mission_ids = [await panel.get_attribute('id') for panel in mission_panels]
        mission_ids = [mission_id.split('_')[-1] for mission_id in mission_ids]

        display_info(f"Found {len(mission_ids)} mission IDs.")

        mission_data = await split_mission_ids_among_threads(mission_ids, browsers, num_threads)

        with open('data/mission_data.json', 'w') as outfile:
            json.dump(mission_data, outfile, indent=4)

        display_info(f"Mission data collection complete. Stored mission data in mission_data.json.")

    except Exception as e:
        display_error(f"Error gathering mission data: {e}")

async def split_mission_ids_among_threads(mission_ids, browsers, num_threads):
    mission_data = {}
    thread_mission_ids = [mission_ids[i::num_threads] for i in range(num_threads)]

    tasks = [gather_mission_info(thread_mission_ids[i], browsers[i], i+1) for i in range(num_threads)]
    results = await asyncio.gather(*tasks)

    for result in results:
        for mission_id, data in result.items():
            if mission_id not in mission_data:
                mission_data[mission_id] = data
    return mission_data

async def gather_mission_info(mission_ids, browser, thread_id):
    mission_data = {}
    page = browser.contexts[0].pages[0]

    for index, mission_id in enumerate(mission_ids):
        try:
            display_info(f"Thread {thread_id}: Grabbing missions {index+1}/{len(mission_ids)}")
            await page.goto(f"https://www.missionchief.com/missions/{mission_id}")
            await page.wait_for_selector('#missionH1', timeout=5000)

            mission_name_element = await page.query_selector('#missionH1')
            if mission_name_element:
                mission_name = (await mission_name_element.inner_text())
            else:
                display_error(f"Mission ID {mission_id}: Mission name element not found.")
                continue

            patient_elements = await page.query_selector_all('.mission_patient')
            patients = len(patient_elements)
            await page.click('#mission_help')
            await page.wait_for_selector('#iframe-inside-container', timeout=5000)
            credits_element = await page.query_selector('td:has-text("Average credits") + td')
            credits_value = int((await credits_element.inner_text()).split()[0]) if credits_element else 0
            max_patients_element = await page.query_selector('td:has-text("Max. Patients") + td')
            max_patients = int((await max_patients_element.inner_text()).strip()) if max_patients_element else 0
            vehicles = await gather_vehicle_requirements(page)
            if max_patients > 0:
                vehicles.append({"name": "Ambulance", "count": max_patients})
            if max_patients >= 10:
                vehicles.append({"name": "EMS Chief", "count": 1})
            if max_patients >= 20:
                vehicles.append({"name": "EMS Mobile Command", "count": 1})
            mission_data[mission_id] = {
                "mission_name": mission_name,
                "credits": credits_value,
                "vehicles": vehicles,
                "patients": patients
                }
        except Exception as e:
            display_error(f"Error processing mission ID {mission_id}: {e}")
    return mission_data

async def gather_vehicle_requirements(page):
    vehicle_requirements = []
    requirement_table = await page.query_selector(
        'div.col-md-4 > table:has(th:has-text("Vehicle and Personnel Requirements"))')

    if requirement_table:
        vehicle_rows = await requirement_table.query_selector_all('tr:has(td:has-text("Required"))')

        for row in vehicle_rows:
            name_element = await row.query_selector('td:first-child')
            count_element = await row.query_selector('td:nth-child(2)')

            if name_element and count_element:
                vehicle_name = (await name_element.text_content()).replace("Required", "").strip().rstrip("s")
                vehicle_count = int((await count_element.text_content()).strip())
                vehicle_requirements.append({"name": vehicle_name, "count": vehicle_count})

    return vehicle_requirements


def parse_missing_vehicles(missing_vehicles_text):
    missing_vehicles = []
    vehicle_parts = missing_vehicles_text.replace('<b>Missing Vehicles:</b>', '').split(',')

    for part in vehicle_parts:
        try:
            count, vehicle_name = part.strip().split(' ', 1)
            count = int(count)
            vehicle_name = vehicle_name.strip().lower()
            missing_vehicles.append({"name": vehicle_name, "count": count})
        except ValueError:
            continue
    return missing_vehicles