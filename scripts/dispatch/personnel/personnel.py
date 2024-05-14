import json
import math
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException


def dispatch_personnel(driver, mission_id, vehicle_pool, mission_data_file, personnel_dispatch_mapping):
    with open(mission_data_file, 'r') as f:
        mission_data = json.load(f)

    current_mission_data = mission_data.get(str(mission_id), {})
    print(current_mission_data)

    if "personnel" in current_mission_data:
        for personnel, required_count in current_mission_data["personnel"].items():
            personnel = personnel.strip()
            vehicle_type_names = personnel_dispatch_mapping.get(personnel.lower(), [])
            if isinstance(vehicle_type_names, str):
                vehicle_type_names = [vehicle_type_names]

            vehicle_type_names = [name.lower().strip() for name in vehicle_type_names]
            required_vehicles = math.ceil(required_count / 6)
            print(vehicle_type_names)
            if not vehicle_type_names:
                print(f"No mapping found for personnel: {personnel}")
                continue
            dispatched_count = 0

            for vehicle_id in list(vehicle_pool.keys()):
                vehicle_info = vehicle_pool[vehicle_id]
                vehicle_name = vehicle_info['name'].lower().strip()  # Lowercase and remove whitespace
                if vehicle_name in vehicle_type_names and dispatched_count < required_vehicles:
                    checkbox_id = f"vehicle_checkbox_{vehicle_id}"
                    try:
                        checkbox = WebDriverWait(driver, 1).until(ec.element_to_be_clickable((By.ID, checkbox_id)))
                        if not checkbox.is_selected():
                            driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                            driver.execute_script("arguments[0].click();", checkbox)
                            print(f"Selected {vehicle_info['name']}:{vehicle_id}")
                            dispatched_count += 1
                            del vehicle_pool[vehicle_id]
                        else:
                            print(f"{vehicle_info['name']} already selected for {personnel}")
                    except (NoSuchElementException, ElementClickInterceptedException, TimeoutException):
                        print(f"Skipping {vehicle_info['name']}:{vehicle_id}")

            if dispatched_count >= required_vehicles:
                break
