import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException


def gather_vehicle_data(driver):
    print("Gathering vehicle data...")
    driver.get('https://missionchief.com/leitstellenansicht')
    time.sleep(10)
    vehicle_urls = [link.get_attribute('href')
                    for link in driver.find_elements(By.CSS_SELECTOR,
                                                     'a.lightbox-open.list-group-item[href*="/vehicles/"]')]

    vehicle_data = {}

    total_vehicles = len(vehicle_urls)
    print(f"Found {total_vehicles} vehicles!")

    current_vehicle_number = 0

    for vehicle_url in vehicle_urls:
        current_vehicle_number += 1
        print(f"Gathering data from vehicle {current_vehicle_number}/{total_vehicles} {vehicle_url}")
        driver.get(vehicle_url)

        WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.TAG_NAME, 'body')))

        vehicle_id = vehicle_url.split('/')[-1]

        try:
            vehicle_name_element = driver.find_element(By.CSS_SELECTOR, 'div#vehicle-attr-type > a')
            vehicle_name = vehicle_name_element.text.strip()
        except NoSuchElementException:
            continue

        vehicle_data[vehicle_id] = {
            'name': vehicle_name,
        }

        with open('data/vehicle_data.json', 'w') as f:
            json.dump(vehicle_data, f)

    for vehicle_id, data in vehicle_data.items():
        print(f"Vehicle ID: {vehicle_id}, Name: {data['name']}")
