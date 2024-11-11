import json

from utils.pretty_print import display_info, display_error

async def navigate_and_dispatch(browsers):
    with open('data/mission_data.json', 'r') as file:
        mission_data = json.load(file)

    page = browsers[0].contexts[0].pages[0]

    for mission_id, data in mission_data.items():
        mission_name = data.get("mission_name", "Unknown Mission")
        display_info(f"Dispatching units for {mission_name}")

        await page.goto(f"https://www.missionchief.com/missions/{mission_id}")
        await page.wait_for_selector('#missionH1', timeout=5000)

        load_missing_button = await page.query_selector('a.missing_vehicles_load.btn-warning')
        if load_missing_button:
            await load_missing_button.click()
            await page.wait_for_load_state('networkidle')
            display_info(f"Loaded additional vehicles for mission {mission_id}")

        vehicle_requirements = data.get("vehicles", [])
        for requirement in vehicle_requirements:
            vehicle_name = requirement["name"]
            vehicle_count = requirement["count"]

            vehicle_ids = await find_vehicle_ids(vehicle_name, vehicle_count)
            if not vehicle_ids:
                display_error(f"Vehicle type '{vehicle_name}' not found in vehicle_data.")
                continue

            display_info(f"Selecting {vehicle_count} unit(s) of type '{vehicle_name}' for mission {mission_id}")
            for vehicle_id in vehicle_ids:
                vehicle_checkbox = await page.query_selector(f'input.vehicle_checkbox[value="{vehicle_id}"]')
                if vehicle_checkbox:
                    await page.evaluate('(checkbox) => checkbox.scrollIntoView()', vehicle_checkbox)
                    await vehicle_checkbox.click()
                    display_info(f"Selected vehicle with ID {vehicle_id} for mission {mission_id}")

async def find_vehicle_ids(vehicle_name, vehicle_count):
    with open('data/vehicle_data.json', 'r') as file:
        vehicle_data = json.load(file)

    vehicle_ids = []
    for vehicle in vehicle_data:
        if vehicle['name'] == vehicle_name and vehicle_count > 0:
            vehicle_ids.append(vehicle['id'])
            vehicle_count -= 1
    return vehicle_ids
