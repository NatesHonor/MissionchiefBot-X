from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException


def dispatch_ems(patients, vehicle_dispatch_mapping, vehicle_pool, driver):
    ems_chief_type = vehicle_dispatch_mapping.get('EMS Chiefs')
    als_ambulance_type = vehicle_dispatch_mapping.get('ambulances', 'Default Ambulance Type')
    if patients >= 10:
        for vehicle_id in list(vehicle_pool.keys()):
            vehicle_info = vehicle_pool[vehicle_id]
            if vehicle_info['name'] == ems_chief_type:
                checkbox_id = f"vehicle_checkbox_{vehicle_id}"
                try:
                    checkbox = WebDriverWait(driver, 1).until(ec.element_to_be_clickable((By.ID, checkbox_id)))
                    if not checkbox.is_selected():
                        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                        driver.execute_script("arguments[0].click();", checkbox)
                        print(f"Selected {ems_chief_type}:{vehicle_id}")
                        del vehicle_pool[vehicle_id]
                        break
                except (NoSuchElementException, ElementClickInterceptedException, TimeoutException):
                    print(f"{ems_chief_type}:{vehicle_id} Already dispatched, continuing...")

    available_ambulances = [vehicle_id for vehicle_id, vehicle_info in vehicle_pool.items() if vehicle_info['name'] ==
                            als_ambulance_type]
    ambulances_to_dispatch = min(patients, len(available_ambulances))
    for i in range(ambulances_to_dispatch):
        vehicle_id = available_ambulances[i]
        checkbox_id = f"vehicle_checkbox_{vehicle_id}"
        try:
            checkbox = WebDriverWait(driver, 1).until(ec.element_to_be_clickable((By.ID, checkbox_id)))
            if not checkbox.is_selected():
                driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                driver.execute_script("arguments[0].click();", checkbox)
                print(f"Selected {als_ambulance_type}:{vehicle_id}")
        except (NoSuchElementException, ElementClickInterceptedException, TimeoutException):
            print(f"Skipping {als_ambulance_type}:{vehicle_id}")

    patients -= ambulances_to_dispatch
