import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


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
