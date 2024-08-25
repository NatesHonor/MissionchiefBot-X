from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
import random
import time
import logging
import configparser

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('config.ini')

def handle_transport_buttons(driver, vehicle_id):
    try:
        transport_buttons = WebDriverWait(driver, 15).until(
            ec.presence_of_all_elements_located((By.XPATH, "//a[starts-with(@id, 'btn_approach_')]"))
        )
        if transport_buttons:
            random.choice(transport_buttons).click()
            logging.info(f"{vehicle_id}: Transport button clicked.")
        else:
            logging.info(f"{vehicle_id}: No transport buttons found.")
    except (NoSuchElementException, TimeoutException) as e:
        logging.error(f"{vehicle_id}: Error finding transport buttons: {e}")

def transport_submit(driver):
    if config.getboolean('transport', 'prisoner_van_handling'):
        # Assuming `van_requests` handles some specific logic for prisoner vans
        from config.prisonervan import van_requests
        van_requests(driver)

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
