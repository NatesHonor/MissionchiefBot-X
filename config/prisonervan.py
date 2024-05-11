import json
import logging
import random

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec


def van_requests(driver):
    with open('data/vehicle_data.json', 'r') as f:
        vehicle_data = json.load(f)

    prisoner_van_ids = [vehicle_id for vehicle_id, info in vehicle_data.items() if
                        info['name'] == 'Police Prisoner Van']

    for vehicle_id in prisoner_van_ids:
        try:
            logging.info(f"{vehicle_id}: Checking for transport request for {vehicle_id}.")
            vehicle_url = f"https://www.missionchief.com/vehicles/{vehicle_id}"
            driver.get(vehicle_url)
        except Exception as e:
            logging.error(f"Error navigating to vehicle {vehicle_id} page: {e}")
            continue
        try:
            transport_buttons = WebDriverWait(driver, 1).until(
                ec.presence_of_all_elements_located(
                    (By.XPATH, "//a[contains(@href, 'gefangener') and contains(@class, 'btn-success')]")))
            random.choice(transport_buttons).click()
            logging.info(f"Running Police Transport for {vehicle_id}.")
        except (NoSuchElementException, TimeoutException):
            logging.info(f"Van {vehicle_id}: has no transport requests.")
