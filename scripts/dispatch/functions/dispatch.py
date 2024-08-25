import logging
import math
import configparser
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from scripts.dispatch.vehicles.tow_truck import dispatch_tow_truck
from scripts.dispatch.vehicles.prisoner_transport import dispatch_police_transport
from scripts.dispatch.personnel.personnel import dispatch_personnel
from scripts.dispatch.functions.select import select_vehicle
from data.mission_utils import remove_mission
config = configparser.ConfigParser()
config.read('config.ini')


def dispatch_vehicles(driver, mission_id, vehicle_pool, mission_requirements,
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
    try:
        load_button = WebDriverWait(driver, 10).until(
            ec.presence_of_element_located(
                (By.CSS_SELECTOR, '.btn.btn-xs.btn-warning.missing_vehicles_load.btn-block')))
        logging.info("Found the load button.")
        driver.execute_script("arguments[0].scrollIntoView();", load_button)
        driver.execute_script("arguments[0].click();", load_button)
        logging.info("Pressed the button to load missing vehicles.")
        time.sleep(2)
    except TimeoutException:
        logging.error("Timeout exception occurred. Button not found within 10 seconds")
    except NoSuchElementException:
        logging.error(f"Could not find the button to load missing vehicles for mission {mission_id}.")
    logging.info("Continuing with dispatching process.")

    dispatch_personnel(driver, mission_id, vehicle_pool, mission_data_file, personnel_dispatch_mapping)
    dispatch_tow_truck(crashed_cars, vehicle_dispatch_mapping, vehicle_pool, driver)
    dispatch_police_transport(prisoners, vehicle_dispatch_mapping, vehicle_pool, driver)

    for requirement, required_count in mission_requirements.items():
        vehicle_type_names = None
        if requirement == "K-9 Unit" and required_count > 2:
            logging.info(f"Dispatching K-9 Carrier instead of K-9 Unit for mission {mission_id}.")
            vehicle_type_names = vehicle_dispatch_mapping.get("k-9 carrier")
            required_count = 1
        elif requirement == "ARFF Unit" and required_count >= 2:
            temp_count = math.ceil(required_count / 2)
            required_count = temp_count
        elif requirement == "SWAT Personnel (In SWAT Vehicles)":
            temp_count = math.ceil(required_count / 6)
            required_count = temp_count
        else:
            vehicle_type_names = vehicle_dispatch_mapping.get(requirement.lower())

        if not vehicle_type_names:
            logging.info(f"No mapping found for requirement: {requirement}. Trying the second mapping...")
            vehicle_type_names = vehicle_dispatch_mapping.get(requirement + "_2")

        if not vehicle_type_names:
            logging.info(f"No mapping found for requirement: {requirement}")
            continue

        if isinstance(vehicle_type_names, list):
            vehicle_types = vehicle_type_names
        else:
            vehicle_types = [vehicle_type_names]

        for vehicle_type in vehicle_types:
            dispatched_count = 0
            matching_vehicles = {vehicle_id: info for vehicle_id, info in vehicle_pool.copy().items() if
                                 vehicle_id in vehicle_type_names}

            for vehicle_id, vehicle_info in matching_vehicles.items():
                if dispatched_count < required_count:
                    if select_vehicle(driver, vehicle_id, vehicle_type):
                        dispatched_count += 1
                        if dispatched_count == required_count:
                            break
            else:
                logging.info(f"Dispatched {dispatched_count} out of {required_count} for {vehicle_type}")
    try:
        if config.get('dispatches', 'dispatch_type') == "alliance":
            dispatch_button = WebDriverWait(driver, 3).until(
                ec.element_to_be_clickable((By.CSS_SELECTOR, '.btn.btn-success.alert_next_alliance')))
        else:
            dispatch_button = WebDriverWait(driver, 3).until(ec.element_to_be_clickable((By.ID, 'alert_btn')))
        driver.execute_script("arguments[0].scrollIntoView();", dispatch_button)
        driver.execute_script("arguments[0].click();", dispatch_button)
        logging.info("Dispatched all selected vehicles.")
    except TimeoutException:
        if config.get('dispatches', 'dispatch_type') == "alliance":
            dispatch_button = WebDriverWait(driver, 3).until(ec.element_to_be_clickable((By.ID, 'alert_btn')))
            driver.execute_script("arguments[0].scrollIntoView();", dispatch_button)
            driver.execute_script("arguments[0].click();", dispatch_button)
        else:
            logging.error("Timeout exception occurred. Dispatch button not found within 3 seconds")
    except NoSuchElementException:
        logging.info(f"Could not find dispatch button for mission {mission_id}.")
