import configparser
import logging
import math

from data.mission_utils import remove_mission
from scripts.dispatch.vehicles.tow_truck import dispatch_tow_truck
from scripts.dispatch.vehicles.als_ambulance import dispatch_ems
from scripts.dispatch.vehicles.prisoner_transport import dispatch_police_transport
from scripts.dispatch.personnel.personnel import dispatch_personnel

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException, TimeoutException

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('config.ini')


def select_vehicle(driver, vehicle_id, vehicle_type_name):
    checkbox_id = f"vehicle_checkbox_{vehicle_id}"
    try:
        checkbox = driver.find_element(By.ID, checkbox_id)
        if checkbox.is_displayed() and checkbox.is_enabled():
            driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
            driver.execute_script("arguments[0].click();", checkbox)
            logging.info(f"Selected {vehicle_type_name}:{vehicle_id}")
            return True
        else:
            logging.info(f"Skipping {vehicle_type_name}:{vehicle_id} as it's not clickable.")
            return False
    except NoSuchElementException:
        logging.info(f"Skipping {vehicle_type_name}:{vehicle_id} as it's already dispatched.")
        return False


def dispatch_vehicles(driver, mission_id, vehicle_pool, mission_requirements, patients,
                      vehicle_dispatch_mapping, crashed_cars, mission_data_file, prisoners, personnel_dispatch_mapping):
    mission_url = f"https://www.missionchief.com/missions/{mission_id}"
    driver.get(mission_url)

    try:
        transport_needed_alert = driver.find_element(By.XPATH, "//*[contains(text(), 'Transport is needed!')]")
        if transport_needed_alert:
            logging.info(f"Skipping mission {mission_id} because it has a transport request.")
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
        vehicle_type_name = None
        if (requirement == "K-9 Unit" or requirement == "K-9 Units") and required_count > 2:
            logging.info(f"Dispatching K-9 Carrier instead of K-9 Unit for mission {mission_id}.")
            vehicle_type_name = vehicle_dispatch_mapping.get("K-9 Carrier")
            required_count = 1
        elif requirement == "ARFF Unit" or requirement == "ARFF Units" and required_count >= 2:
            temp_count = math.ceil(required_count / 2)
            required_count = temp_count
        elif requirement == "SWAT Personnel (In SWAT Vehicles)":
            temp_count = math.ceil(required_count / 6)
            required_count = temp_count
        else:
            vehicle_type_name = vehicle_dispatch_mapping.get(requirement)

        if not vehicle_type_name:
            logging.info(f"No mapping found for requirement: {requirement}. Trying the second mapping...")
            vehicle_type_name = vehicle_dispatch_mapping.get(requirement + "_2")

        if not vehicle_type_name:
            logging.info(f"No mapping found for requirement: {requirement}")
            continue

        if isinstance(vehicle_type_name, list):
            dispatched_count = 0
            for v_type_name in vehicle_type_name:
                matching_vehicles = {vehicle_id: info for vehicle_id, info in vehicle_pool.copy().items() if
                                     info['name'] == v_type_name}

                for vehicle_id, vehicle_info in matching_vehicles.items():
                    if dispatched_count < required_count:
                        if select_vehicle(driver, vehicle_id, v_type_name):
                            dispatched_count += 1
                            break
                else:
                    logging.info(f"Dispatched {dispatched_count} out of {required_count} for {v_type_name}")
                    break
        else:
            dispatched_count = 0
            matching_vehicles = {vehicle_id: info for vehicle_id, info in vehicle_pool.copy().items() if
                                 info['name'] == vehicle_type_name}

            for vehicle_id, vehicle_info in matching_vehicles.items():
                if dispatched_count < required_count:
                    if select_vehicle(driver, vehicle_id, vehicle_type_name):
                        dispatched_count += 1
                        if dispatched_count == required_count:
                            break
            else:
                logging.info(f"Dispatched {dispatched_count} out of {required_count} for {vehicle_type_name}")

    try:
        if config.get('dispatches', 'dispatch_type') == "alliance":
            dispatch_button = WebDriverWait(driver, 10).until(
                ec.element_to_be_clickable((By.CSS_SELECTOR, '.btn.btn-success.alert_next_alliance')))
        else:
            dispatch_button = WebDriverWait(driver, 3).until(ec.element_to_be_clickable((By.ID, 'alert_btn')))
        driver.execute_script("arguments[0].scrollIntoView();", dispatch_button)
        driver.execute_script("arguments[0].click();", dispatch_button)
        logging.info("Dispatched all selected vehicles.")
    except TimeoutException:
        dispatch_button = WebDriverWait(driver, 10).until(ec.element_to_be_clickable((By.ID, 'alert_btn')))
        driver.execute_script("arguments[0].scrollIntoView();", dispatch_button)
        driver.execute_script("arguments[0].click();", dispatch_button)
    except NoSuchElementException:
        logging.info(f"Could not find dispatch button for mission {mission_id}.")
