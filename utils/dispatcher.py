import json

from utils.pretty_print import display_info, display_error
from utils.vehicle_options import get_vehicle_options


async def navigate_and_dispatch(browsers):
    with open('data/mission_data.json', 'r') as file:
        mission_data = json.load(file)

    page = browsers[0].contexts[0].pages[0]

    for mission_id, data in mission_data.items():
        mission_name = data.get("mission_name", "Unknown Mission")
        display_info(f"Dispatching units for {mission_name}")
        await page.goto(f"https://www.missionchief.com/missions/{mission_id}")
        try:
            await page.wait_for_selector('#missionH1', timeout=5000)
        except TimeoutError:
            display_error(f"Mission {mission_id} didn't load in time. Possible slow network? Skipping mission...")
            continue

        load_missing_button = await page.query_selector('a.missing_vehicles_load.btn-warning')
        if load_missing_button:
            await load_missing_button.click()
            await page.wait_for_load_state('networkidle')
            display_info(f"Loaded additional vehicles for mission {mission_id}")

        vehicle_requirements = data.get("vehicles", [])
        for requirement in vehicle_requirements:
            vehicle_name = requirement["name"]
            vehicle_count = requirement["count"]
            if "SWAT Personnel" in vehicle_name:
                armoured_vehicles_needed = vehicle_count // 6
                armoured_vehicle_ids = await find_vehicle_ids("SWAT Armoured Vehicle")
                selected_count = 0
                for vehicle_id in armoured_vehicle_ids:
                    if selected_count >= armoured_vehicles_needed:
                        break
                    vehicle_checkbox = await page.query_selector(f'input.vehicle_checkbox[value="{vehicle_id}"]')
                    if vehicle_checkbox:
                        await page.evaluate('(checkbox) => checkbox.scrollIntoView()', vehicle_checkbox)
                        await vehicle_checkbox.click()
                        display_info(f"Selected SWAT Armored Vehicle({vehicle_id})")
                        selected_count += 1

                if selected_count < armoured_vehicles_needed:
                    swat_suv_ids = await find_vehicle_ids("SWAT SUV")
                    for vehicle_id in swat_suv_ids:
                        if selected_count >= vehicle_count:
                            break
                        vehicle_checkbox = await page.query_selector(f'input.vehicle_checkbox[value="{vehicle_id}"]')
                        if vehicle_checkbox:
                            await page.evaluate('(checkbox) => checkbox.scrollIntoView()', vehicle_checkbox)
                            await vehicle_checkbox.click()
                            display_info(f"Selected SWAT SUV({vehicle_id})")
                            selected_count += 1

            else:
                vehicle_ids = await find_vehicle_ids(vehicle_name)
                if not vehicle_ids:
                    display_error(f"Vehicle type '{vehicle_name}' not found in vehicle_data.")
                    continue
                display_info(f"Selecting {vehicle_count} unit(s) of type '{vehicle_name}' for mission {mission_id}")
                selected_count = 0
                for vehicle_id in vehicle_ids:
                    if selected_count >= vehicle_count:
                        break
                    vehicle_checkbox = await page.query_selector(f'input.vehicle_checkbox[value="{vehicle_id}"]')
                    if vehicle_checkbox:
                        await page.evaluate('(checkbox) => checkbox.scrollIntoView()', vehicle_checkbox)
                        await vehicle_checkbox.click()
                        display_info(f"Selected Vehicle {vehicle_name}({vehicle_id})")
                        selected_count += 1

        dispatch_button = await page.query_selector('#alert_btn')
        if dispatch_button:
            await dispatch_button.click()
            display_info(f"Dispatched units for mission {mission_id}")
        else:
            display_error(f"Dispatch button not found for mission {mission_id}")


async def find_vehicle_ids(vehicle_name):
    with open('data/vehicle_data.json', 'r') as file:
        vehicle_data = json.load(file)
    vehicle_ids = []
    if vehicle_name in vehicle_data:
        vehicle_ids.extend(vehicle_data[vehicle_name])
    alternatives = get_vehicle_options(vehicle_name)
    if alternatives:
        display_info(f"Gathering alternative types for '{vehicle_name}': {', '.join(alternatives)}")
        for alt_name in alternatives:
            if alt_name in vehicle_data:
                vehicle_ids.extend(vehicle_data[alt_name])
    if not vehicle_ids:
        display_error(f"No vehicles found for '{vehicle_name}' or its alternatives.")
    return vehicle_ids
