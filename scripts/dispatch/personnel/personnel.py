import json
import math
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException


def dispatch_personnel(driver, mission_id, vehicle_pool, mission_data_file, personnel_dispatch_mapping):
    with open(mission_data_file, 'r') as f:
        mission_data = json.load(f)

    current_mission_data = mission_data.get(str(mission_id), {})
    print(current_mission_data)

    if "personnel" in current_mission_data:
        for personnel, required_count in current_mission_data["personnel"].items():
            if personnel == "EMS Mobile Command":
                vehicle_type_name = personnel_dispatch_mapping.get("EMS Mobile Command")
                required_vehicles = math.ceil(required_count / 3)
            else:
                vehicle_type_name = personnel_dispatch_mapping.get(personnel)
                required_vehicles = math.ceil(required_count / 6)

            if not vehicle_type_name:
                print(f"No mapping found for personnel: {personnel}")
                continue
            dispatched_count = 0
            print(f"required vehicles required_vehicles: {required_vehicles}")
            for vehicle_id in list(vehicle_pool.keys()):
                vehicle_info = vehicle_pool[vehicle_id]
                if vehicle_info['name'] == vehicle_type_name and dispatched_count < required_vehicles:
                    checkbox_id = f"vehicle_checkbox_{vehicle_id}"
                    try:
                        checkbox = WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.ID, checkbox_id)))
                        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                        driver.execute_script("arguments[0].click();", checkbox)
                        dispatched_count += 1
                        print(f"Vehicle {vehicle_type_name}:{vehicle_id} selected.")
                        del vehicle_pool[vehicle_id]
                    except TimeoutException:
                        print(f"Skipping {vehicle_type_name}:{vehicle_id}.")
                        continue
                    except ElementClickInterceptedException:
                        print(
                            f"ElementClickInterceptedException for vehicle ID {vehicle_id},"
                            f" trying alternative click method.")
                        driver.execute_script("arguments[0].click();", checkbox)
