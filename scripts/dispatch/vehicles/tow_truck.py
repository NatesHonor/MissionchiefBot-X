from selenium.common import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec


def dispatch_tow_truck(crashed_cars, vehicle_dispatch_mapping, vehicle_pool, driver):
    if crashed_cars > 0:
        if crashed_cars == 1:
            recovery_vehicle_type = vehicle_dispatch_mapping['Wreckers']
        elif crashed_cars == 2:
            recovery_vehicle_type = vehicle_dispatch_mapping['Flatbed Carriers']
        else:
            recovery_vehicle_type = [vehicle_dispatch_mapping['Wreckers'], vehicle_dispatch_mapping['Flatbed Carriers']]

        dispatched_recovery_vehicles = 0
        for vehicle_id in list(vehicle_pool.keys()):
            if dispatched_recovery_vehicles >= crashed_cars:
                break
            vehicle_info = vehicle_pool[vehicle_id]
            if isinstance(recovery_vehicle_type, list):
                for recovery_type in recovery_vehicle_type:
                    if vehicle_info['name'] == recovery_type:
                        dispatch_recovery_vehicle(driver, vehicle_pool, recovery_type, crashed_cars)
                        dispatched_recovery_vehicles += 1
            else:
                if vehicle_info['name'] == recovery_vehicle_type:
                    dispatch_recovery_vehicle(driver, vehicle_pool, recovery_vehicle_type, crashed_cars)
                    dispatched_recovery_vehicles += 1


def dispatch_recovery_vehicle(driver, vehicle_pool, recovery_vehicle_type, crashed_cars):
    dispatched_recovery_vehicles = 0
    for vehicle_id in list(vehicle_pool.keys()):
        vehicle_info = vehicle_pool[vehicle_id]
        if vehicle_info['name'] == recovery_vehicle_type:
            checkbox_id = f"vehicle_checkbox_{vehicle_id}"
            try:
                checkbox = WebDriverWait(driver, 1).until(ec.element_to_be_clickable((By.ID, checkbox_id)))
                if not checkbox.is_selected():
                    driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                    driver.execute_script("arguments[0].click();", checkbox)
                    print(f"Vehicle {recovery_vehicle_type}:{vehicle_id} selected.")
                    if recovery_vehicle_type == 'Flatbed Carrier':
                        dispatched_recovery_vehicles += 2
                    else:
                        dispatched_recovery_vehicles += 1
                    print(f"Dispatched vehicles: {dispatched_recovery_vehicles}, Crashed cars: {crashed_cars}")
                if dispatched_recovery_vehicles >= crashed_cars:
                    break
            except NoSuchElementException:
                print(f"Skipping {recovery_vehicle_type}:{vehicle_id}. Element not found.")
                continue
            except ElementClickInterceptedException:
                print(f"Skipping {recovery_vehicle_type}:{vehicle_id}. Element not clickable.")
                continue
            except TimeoutException:
                print(f"Skipping {recovery_vehicle_type}:{vehicle_id}. Timeout exceeded.")
                continue
