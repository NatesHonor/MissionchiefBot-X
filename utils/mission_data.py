import asyncio
import json
import os
import re

from utils.pretty_print import display_info, display_error

async def check_and_grab_missions(browsers, num_threads):
    first_browser = browsers[0]
    try:
        if os.path.exists('data/mission_data.json'):
            os.remove('data/mission_data.json')
        page = first_browser.contexts[0].pages[0]
        await page.goto("https://www.missionchief.com")
        mission_panels = await page.query_selector_all('.mission_panel_red')
        if not mission_panels:
            display_info("No missions found, skipping this function.")
            return
        mission_ids = [await panel.get_attribute('id') for panel in mission_panels]
        mission_ids = [mission_id.split('_')[-1] for mission_id in mission_ids]
        display_info(f"Found {len(mission_ids)} mission IDs.")
        mission_data = await split_mission_ids_among_threads(mission_ids, browsers, num_threads)
        with open('data/mission_data.json', 'w') as outfile:
            json.dump(mission_data, outfile, indent=4)
        display_info("Mission data collection complete. Stored mission data in mission_data.json.")
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
        skip_this_mission = False

        try:
            display_info(f"Thread {thread_id}: Grabbing missions {index+1}/{len(mission_ids)}")
            await page.goto(f"https://www.missionchief.com/missions/{mission_id}")
            await page.wait_for_selector('#missionH1', timeout=5000)

            mission_name_element = await page.query_selector('#missionH1')
            if mission_name_element:
                mission_name = (await mission_name_element.inner_text()).strip()
            else:
                display_error(f"Mission ID {mission_id}: Mission name element not found.")
                continue
            try:
                vehicles = []
                crashed_cars = 0
                alerts = await page.query_selector_all('div.alert.alert-danger')
                for alert in alerts:
                    text = (await alert.inner_text()).strip().lower()
                    if "missing vehicles:" in text:
                        text = text.replace('\xa0', ' ').replace('missing vehicles:', '').strip()
                        vehicle_entries = text.split(',')
                        for entry in vehicle_entries:
                            match = re.search(r'(\d+)\s+(.+)', entry.strip())
                            if match:
                                count = int(match.group(1))
                                name = match.group(2).strip().lower()

                                if name.endswith('s'):
                                    name = name[:-1]
                                    if name == "car to tow":
                                        crashed_cars = count
                                    else:
                                        vehicles.append({"name": name, "count": count})

                        mission_data[mission_id] = {
                            "mission_name": f"Missing Vehicles Mission {mission_id}",
                            "credits": 0,
                            "vehicles": vehicles,
                            "patients": 0,
                            "crashed_cars": crashed_cars,
                            "required_personnel": []
                        }
                        display_info(f"Thread {thread_id}: Mission {mission_id} has missing vehicles.")
                        skip_this_mission = True
                        break
            except Exception as e:
                display_error(f"Thread {thread_id}: Error parsing missing vehicles: {e}")
            try:
                if not skip_this_mission:
                    alerts = await page.query_selector_all('div.alert.alert-danger')
                    for alert in alerts:
                        text = (await alert.inner_text()).strip().lower()
                        if "prisoners must be transported" in text or "transport is needed!" in text:
                            display_info(f"Thread {thread_id}: Prisoner transport required for mission {mission_id}")
                            transport_successful = await handle_prisoner_transport(page)

                            if not transport_successful:
                                prisoner_h4 = await page.query_selector('#h2_prisoners')
                                prisoner_count = 0
                                if prisoner_h4:
                                    prisoner_text = (await prisoner_h4.inner_text()).strip()
                                    match = re.search(r'(\d+)', prisoner_text)
                                    if match:
                                        prisoner_count = int(match.group(1))
                                mission_data[mission_id] = {
                                    "mission_name": f"Prisoner Transport Mission {mission_id}",
                                    "credits": 0,
                                    "vehicles": [],
                                    "patients": 0,
                                    "crashed_cars": 0,
                                    "required_personnel": [
                                        {"name": "Prisoners", "count": prisoner_count}
                                    ]
                                }
                                display_info(f"Thread {thread_id}: Skipping mission {mission_id} due to no transport vehicles.")
                                skip_this_mission = True
                            break
            except Exception as e:
                display_error(f"Thread {thread_id}: Error handling prisoner transport check: {e}")

            if skip_this_mission:
                continue
            await page.click('#mission_help')
            await page.wait_for_selector('#iframe-inside-container', timeout=5000)

            vehicles = await gather_vehicle_requirements(page)

            credits_element = await page.query_selector('td:has-text("Average credits") + td')
            credits_value = int((await credits_element.inner_text()).split()[0]) if credits_element else 0

            patients_element = await page.query_selector('td:has-text("Max. Patients") + td')
            patients = int((await patients_element.inner_text()).strip()) if patients_element else 0

            crashed_cars_element = await page.query_selector('td:has-text("Maximum amount of cars to tow") + td')
            crashed_cars = int((await crashed_cars_element.inner_text()).strip()) if crashed_cars_element else 0

            required_personnel = []
            personnel_elements = await page.query_selector_all('td:has-text("Required Personnel Available") + td div')
            for element in personnel_elements:
                text = (await element.inner_text()).strip()
                if 'x' in text:
                    count, name = text.split('x', 1)
                    required_personnel.append({"name": name.strip(), "count": int(count.strip())})

            if patients > 0:
                vehicles.append({"name": "ambulance", "count": patients})
            if patients >= 10:
                vehicles.append({"name": "ems chief", "count": 1})
            if patients >= 20:
                vehicles.append({"name": "ems mobile command unit", "count": 1})

            mission_data[mission_id] = {
                "mission_name": mission_name,
                "credits": credits_value,
                "vehicles": vehicles,
                "patients": patients,
                "crashed_cars": crashed_cars,
                "required_personnel": required_personnel
            }
        except Exception as e:
            display_error(f"Error processing mission ID {mission_id}: {e}")

    return mission_data


def remove_plural_suffix(vehicle_name):
    vehicle_name_parts = vehicle_name.split()
    if vehicle_name_parts[-1].endswith('s'):
        vehicle_name_parts[-1] = vehicle_name_parts[-1][:-1]
    return ' '.join(vehicle_name_parts)


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
                vehicle_name = (await name_element.text_content()).replace("Required", "").strip()
                vehicle_name = remove_plural_suffix(vehicle_name)
                vehicle_count = int((await count_element.text_content()).strip())
                if "Probability" in vehicle_name:
                    continue
                vehicle_requirements.append({"name": vehicle_name, "count": vehicle_count})

    return vehicle_requirements

async def handle_prisoner_transport(page):
    try:
        while True:
            prison_select_divs = await page.query_selector_all('div.prison-select')
            sorted_prison_buttons = []
            for div in prison_select_divs:
                green_buttons = await div.query_selector_all('a.btn-success')
                for btn in green_buttons:
                    distance = await extract_distance(btn)
                    sorted_prison_buttons.append((distance, btn, 'green'))
                yellow_buttons = await div.query_selector_all('a.btn-warning')
                for btn in yellow_buttons:
                    distance = await extract_distance(btn)
                    sorted_prison_buttons.append((distance, btn, 'yellow'))
            if sorted_prison_buttons:
                sorted_prison_buttons.sort(key=lambda x: x[0])
                _, closest_button, btn_type = sorted_prison_buttons[0]
                prison_name = await closest_button.inner_text()
                display_info(f"Clicking {btn_type} transport button for {prison_name}")
                await closest_button.click()
                await page.wait_for_load_state('networkidle')
                continue
            return False
    except Exception as e:
        display_error(f"Error in prisoner transport handler: {e}")
        return False



async def extract_distance(button):
    try:
        text = await button.inner_text()
        match = re.search(r'Distance: ([\d.]+) km', text)
        if match:
            return float(match.group(1))
    except:
        pass
    return float('inf')