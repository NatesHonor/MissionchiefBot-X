import math

from selenium.common import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec


def dispatch_police_transport(prisoners, vehicle_dispatch_mapping, vehicle_pool, driver):
    if prisoners > 1:
        prisoner_vehicle = vehicle_dispatch_mapping['prisoner transport']
        required_vehicles = math.ceil(prisoners / 6)

        dispatched_count = 0
        for vehicle_id in list(vehicle_pool.keys()):
            if dispatched_count >= required_vehicles:
                break

            vehicle_info = vehicle_pool[vehicle_id]
            if isinstance(prisoner_vehicle, list):
                for recovery_type in prisoner_vehicle:
                    if vehicle_info['name'] == recovery_type:
                        dispatched_count += dispatch_prisoner_van(driver, vehicle_pool, vehicle_id, recovery_type)
            else:
                if vehicle_info['name'] == prisoner_vehicle:
                    dispatched_count += dispatch_prisoner_van(driver, vehicle_pool, vehicle_id, prisoner_vehicle)


def dispatch_prisoner_van(driver, vehicle_pool, vehicle_id, recovery_vehicle_type):
    vehicle_info = vehicle_pool[vehicle_id]
    if vehicle_info['name'] == recovery_vehicle_type:
        checkbox_id = f"vehicle_checkbox_{vehicle_id}"
        try:
            checkbox = WebDriverWait(driver, 1).until(ec.element_to_be_clickable((By.ID, checkbox_id)))
            if not checkbox.is_selected():
                ActionChains(driver).move_to_element(checkbox).perform()
                driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                driver.execute_script("arguments[0].click();", checkbox)
                print(f"Vehicle {recovery_vehicle_type}:{vehicle_id} selected.")
                del vehicle_pool[vehicle_id]
                return 1
        except (NoSuchElementException, ElementClickInterceptedException, TimeoutException):
            print(f"Skipping:  {recovery_vehicle_type}:{vehicle_id}")
    return 0
