import configparser

from data.mission_utils import remove_mission
from scripts.dispatch.vehicles.tow_truck import dispatch_tow_truck
from scripts.dispatch.vehicles.als_ambulance import dispatch_ems
from scripts.dispatch.vehicles.prisoner_transport import dispatch_police_transport
from scripts.dispatch.personnel.personnel import dispatch_personnel

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException

config = configparser.ConfigParser()
config.read('config.ini')


def dispatch_vehicles(driver, mission_id, vehicle_pool, mission_requirements, patients,
                      vehicle_dispatch_mapping, crashed_cars, mission_data_file, prisoners, personnel_dispatch_mapping):
    mission_url = f"https://www.missionchief.com/missions/{mission_id}"
    driver.get(mission_url)

    try:
        transport_needed_alert = driver.find_element(By.XPATH, "//*[contains(text(), 'Transport is needed!')]")
        if transport_needed_alert:
            print(f"Skipping mission {mission_id} because it has a transport request.")
            return
    except NoSuchElementException:
        pass

    try:
        WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.ID, 'all')))
    except TimeoutException:
        remove_mission(mission_id, mission_data_file)
        return

    dispatch_personnel(driver, mission_id, vehicle_pool, mission_data_file, personnel_dispatch_mapping)
    dispatch_tow_truck(crashed_cars, vehicle_dispatch_mapping, vehicle_pool, driver)
    dispatch_police_transport(prisoners, vehicle_dispatch_mapping, vehicle_pool, driver)
    dispatch_ems(patients, vehicle_dispatch_mapping, vehicle_pool, driver)

    for requirement, required_count in mission_requirements.items():
        if (requirement == "K-9 Unit" or requirement == "K-9 Units") and required_count > 2:
            print(f"Dispatching K-9 Carrier instead of K-9 Unit for mission {mission_id}.")
            vehicle_type_name = vehicle_dispatch_mapping["K-9 Carrier"]
            required_count = 1
        else:
            vehicle_type_name = vehicle_dispatch_mapping[requirement]
        dispatched_count = 0
        if not vehicle_type_name:
            print(f"No mapping found for requirement: {requirement}")
            continue
        matching_vehicles = {vehicle_id: info for vehicle_id, info in vehicle_pool.copy().items() if
                             info['name'] == vehicle_type_name}
        vehicle_ids_to_delete = []
        for vehicle_id, vehicle_info in matching_vehicles.items():
            if dispatched_count < required_count:
                checkbox_id = f"vehicle_checkbox_{vehicle_id}"
                try:
                    checkbox = WebDriverWait(driver, 0).until(ec.element_to_be_clickable((By.ID, checkbox_id)))
                    driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                    driver.execute_script("arguments[0].click();", checkbox)
                    dispatched_count += 1
                    print(f"Selected {vehicle_type_name}:{vehicle_id}")
                    if dispatched_count == required_count:
                        break
                except TimeoutException:
                    print(f"Skipping {vehicle_type_name}:{vehicle_id}.")
                    continue
                except ElementClickInterceptedException:
                    checkbox = WebDriverWait(driver, 0).until(ec.element_to_be_clickable((By.ID, checkbox_id)))
                    print(
                        f"ElementClickInterceptedException for vehicle ID {vehicle_id},"
                        f" trying alternative click method.")
                    driver.execute_script("arguments[0].click();", checkbox)
                except (NoSuchElementException, TimeoutException):
                    print(f"Skipping {vehicle_type_name}:{vehicle_id}.")
                    continue
                vehicle_ids_to_delete.append(vehicle_id)

        for vehicle_id in vehicle_ids_to_delete:
            del vehicle_pool[vehicle_id]

    try:
        if config.get('dispatches', 'dispatch_type') == "alliance":
            dispatch_button = WebDriverWait(driver, 10).until(
                ec.element_to_be_clickable((By.CSS_SELECTOR, '.btn.btn-success.alert_next_alliance')))
        else:
            dispatch_button = WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.ID, 'alert_btn')))
        driver.execute_script("arguments[0].scrollIntoView();", dispatch_button)
        driver.execute_script("arguments[0].click();", dispatch_button)
        print("Dispatched all selected vehicles.")
    except NoSuchElementException:
        print(f"Could not find dispatch button for mission {mission_id}.")
