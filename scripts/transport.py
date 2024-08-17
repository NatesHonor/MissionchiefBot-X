from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

import random
import time
from config.prisonervan import van_requests
import logging
import configparser

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('config.ini')

from scripts.missions.transport_needed import transport_vehicle_ids

def transport_submit(driver):
    if config.getboolean('transport', 'prisoner_van_handling'):
        van_requests(driver)

    try:
        driver.get("https://www.missionchief.com")
    except Exception as e:
        logging.error(f"Error navigating to Mission Chief: {e}")
        return

    try:
        WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.TAG_NAME, 'body')))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        if transport_vehicle_ids:
            for vehicle_id in transport_vehicle_ids:
                vehicle_url = f"https://www.missionchief.com/vehicles/{vehicle_id}"
                driver.get(vehicle_url)
                transport_buttons = WebDriverWait(driver, 5).until(
                    ec.presence_of_all_elements_located((By.XPATH, "//a[starts-with(@id, 'btn_approach_')]")))
                random.choice(transport_buttons).click()
            return

        transport_requests = driver.find_elements(By.XPATH, "//li[starts-with(@class, 'radio_message_vehicle_')]")
    except Exception as e:
        logging.error(f"Error finding transport requests: {e}")
        return

    vehicle_ids = [request.get_attribute('class').split('_')[-1] for request in transport_requests]
    logging.info(f"Vehicle IDs: {vehicle_ids}")

    for vehicle_id in vehicle_ids:
        try:
            logging.info(f"{vehicle_id}: Transporting")
            vehicle_url = f"https://www.missionchief.com/vehicles/{vehicle_id}"
            driver.get(vehicle_url)
        except Exception as e:
            logging.error(f"Error navigating to vehicle {vehicle_id} page: {e}")
            continue

        try:
            transport_buttons = WebDriverWait(driver, 5).until(
                ec.presence_of_all_elements_located((By.XPATH, "//a[starts-with(@id, 'btn_approach_')]")))
            random.choice(transport_buttons).click()
        except (NoSuchElementException, TimeoutException):
            logging.info(f"Ambulance dispatch button not found {vehicle_id}, Trying police dispatch button.")
            try:
                transport_buttons = WebDriverWait(driver, 5).until(
                    ec.presence_of_all_elements_located(
                        (By.XPATH, "//a[contains(@href, 'gefangener') and contains(@class, 'btn-success')]")))
                random.choice(transport_buttons).click()
                logging.info(f"Running Police Transport for {vehicle_id}.")
            except (NoSuchElementException, TimeoutException) as e:
                logging.error(f"Exception occurred while running police transport for {vehicle_id}: {e}")

                try:
                    wait = WebDriverWait(driver, 5)
                    button = wait.until(ec.element_to_be_clickable((By.CLASS_NAME, 'btn btn-default btn-sm')))
                    button.click()
                    logging.info(f"Detected 0 available transport locations, leaving civilian at scene...")
                    try:
                        prisoner_leave_button = WebDriverWait(driver, 5).until(
                            ec.element_to_be_clickable((By.CSS_SELECTOR, 'a.btn.btn-xs.btn-danger')))
                        prisoner_leave_button.click()
                        logging.info(f"Attempted to leave prisoner at the scene for vehicle {vehicle_id}.")
                    except (NoSuchElementException, TimeoutException) as e:
                        logging.error(f"Exception occurred while leaving prisoner at scene {vehicle_id}: {e}")
                        continue

                except (NoSuchElementException, TimeoutException):
                    logging.error(f"Unable to leave patient at scene for {vehicle_id}")
                    continue
