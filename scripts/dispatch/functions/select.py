import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
debug = config.getboolean('client', 'debug', fallback=False)

def select_vehicle(driver, vehicle_id, vehicle_type_name):
    checkbox_id = f"vehicle_checkbox_{vehicle_id}"
    attempts = 0
    while attempts < 3:
        try:
            checkbox = driver.find_element(By.ID, checkbox_id)
            if checkbox.is_displayed() and checkbox.is_enabled():
                driver.execute_script("arguments[0].click();", checkbox)
                logging.info(f"Selected {vehicle_type_name}:{vehicle_id}")
                return True
            else:
                if debug:
                    logging.info(f"Skipping {vehicle_type_name}:{vehicle_id} as it is not visible or enabled.")
                return False
        except (NoSuchElementException, ElementNotInteractableException):
            if debug:
                logging.info(f"Skipping {vehicle_type_name}:{vehicle_id} as it does not exist or is not interactable.")
            return False
        except StaleElementReferenceException:
            attempts += 1
            logging.info(f"Retrying to locate {vehicle_type_name}:{vehicle_id} due to stale element reference.")
    return False

def select_vehicles(driver, vehicle_ids, vehicle_type_name, required_count):
    dispatched_count = 0
    for vehicle_id in vehicle_ids:
        if dispatched_count < required_count:
            if select_vehicle(driver, vehicle_id, vehicle_type_name):
                dispatched_count += 1
        else:
            break
    return dispatched_count
