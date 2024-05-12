import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def select_vehicle(driver, vehicle_id, vehicle_type_name):
    checkbox_id = f"vehicle_checkbox_{vehicle_id}"
    try:
        checkbox = driver.find_element(By.ID, checkbox_id)
        if checkbox.is_displayed() and checkbox.is_enabled():
            driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
            driver.execute_script("arguments[0].click();", checkbox)
            logging.info(f"Selected {vehicle_type_name.lower()}:{vehicle_id}")
            return True
        else:
            logging.info(f"Skipping {vehicle_type_name.lower()}:{vehicle_id} as it's not clickable.")
            return False
    except NoSuchElementException:
        logging.info(f"Skipping {vehicle_type_name.lower()}:{vehicle_id} as it's already dispatched.")
        return False


def dispatch_ems(patients, vehicle_dispatch_mapping, vehicle_pool, driver):
    ems_chief_type = vehicle_dispatch_mapping.get('ems chief').lower()
    als_ambulance_type = vehicle_dispatch_mapping.get('ambulance').lower()
    if patients >= 10 and ems_chief_type in [v['name'].lower() for v in vehicle_pool.values()]:
        for vehicle_id, vehicle_info in vehicle_pool.items():
            if vehicle_info['name'].lower() == "ems chief":
                checkbox_id = f"vehicle_checkbox_{vehicle_id}"
                try:
                    checkbox = WebDriverWait(driver, 1).until(ec.element_to_be_clickable((By.ID, checkbox_id)))
                    if not checkbox.is_selected():
                        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                        driver.execute_script("arguments[0].click();", checkbox)
                        print(f"Selected {ems_chief_type}:{vehicle_id}")
                        break
                except TimeoutException:
                    print(f"Skipping {ems_chief_type}:{vehicle_id} as it's not clickable.")

    dispatched_count = 0
    available_ambulances = {vehicle_id: info for vehicle_id, info in vehicle_pool.copy().items() if
                            info['name'].lower() == als_ambulance_type}

    if available_ambulances:
        for vehicle_id, vehicle_info in available_ambulances.items():
            if dispatched_count < patients:
                if select_vehicle(driver, vehicle_id, als_ambulance_type):
                    dispatched_count += 1
                    if dispatched_count == patients:
                        break
