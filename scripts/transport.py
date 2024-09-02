from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

import time
import logging
import configparser

from scripts.dispatch.functions.check import wait_for_element

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('config.ini')

def handle_transport_buttons(driver, vehicle_id):
    try:
        transport_buttons = WebDriverWait(driver, 15).until(
            ec.presence_of_all_elements_located((By.XPATH, "//a[contains(@class, 'btn btn-success')]"))
        )
        if transport_buttons:
            clicked = False
            for button in transport_buttons:
                try:
                    button.click()
                    logging.info(f"{vehicle_id}: Transport button clicked.")
                    clicked = True
                    break
                except ElementNotInteractableException:
                    continue
            if not clicked:
                logging.info(f"{vehicle_id}: No transport buttons were clickable.")
                release_prisoners(driver, vehicle_id)
        else:
            logging.info(f"{vehicle_id}: No transport buttons found.")
            release_prisoners(driver, vehicle_id)
    except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
        logging.error(f"{vehicle_id}: Error finding transport buttons: {e}")
        release_prisoners(driver, vehicle_id)

def release_prisoners(driver, vehicle_id):
    try:
        release_button = driver.find_element(By.XPATH, "//a[contains(@class, 'btn btn-xs btn-danger') and contains(@href, 'entlassen')]")
        release_button.click()
        logging.info(f"{vehicle_id}: No transport buttons available. Released prisoners.")
    except NoSuchElementException:
        logging.error(f"{vehicle_id}: No release button found.")

def transport_submit(driver):
    if config.getboolean('transport', 'prisoner_van_handling'):
        from config.prisonervan import van_requests
        van_requests(driver)
    wait_for_element(driver, 'all')
    try:
        driver.get("https://www.missionchief.com")
        logging.info("Navigating to Missionchief")
        WebDriverWait(driver, 30).until(ec.presence_of_element_located((By.TAG_NAME, 'body')))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        transport_requests = WebDriverWait(driver, 15).until(
            ec.presence_of_all_elements_located((By.XPATH, "//li[starts-with(@class, 'radio_message_vehicle_')]"))
        )
        logging.info("Transport requests found")

        vehicle_ids = [request.get_attribute('class').split('_')[-1] for request in transport_requests]
        logging.info(f"Vehicle IDs: {vehicle_ids}")

        for vehicle_id in vehicle_ids:
            try:
                vehicle_url = f"https://www.missionchief.com/vehicles/{vehicle_id}"
                driver.get(vehicle_url)
                logging.info(f"Processing vehicle {vehicle_id}")
                handle_transport_buttons(driver, vehicle_id)
            except Exception as e:
                logging.error(f"Error processing vehicle {vehicle_id}: {e}")

    except (NoSuchElementException, TimeoutException) as e:
        logging.error(f"Error processing transport requests: {e}")
        logging.info("Sleeping for 60 seconds...")
        time.sleep(60)
