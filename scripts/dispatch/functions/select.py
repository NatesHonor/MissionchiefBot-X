import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
debug = config.getboolean('client', 'debug', fallback=False)

def select_vehicle(driver, vehicle_id, vehicle_type_name):
    checkbox_id = f"vehicle_checkbox_{vehicle_id}"
    try:
        checkbox = driver.find_element(By.ID, checkbox_id)
        if checkbox.is_displayed() and checkbox.is_enabled():
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
            driver.execute_script("arguments[0].click();", checkbox)
            logging.info(f"Selected {vehicle_type_name}:{vehicle_id}")
            return True
        else:
            if debug:
                logging.info(f"Skipping {vehicle_type_name}:{vehicle_id} as it is not visible or enabled.")
            return False
    except NoSuchElementException:
        if debug:
            logging.info(f"Skipping {vehicle_type_name}:{vehicle_id} as it does not exist.")
        return False
    except ElementNotInteractableException:
        if debug:
            logging.info(f"Skipping {vehicle_type_name}:{vehicle_id} as it's not interactable.")
        return False
