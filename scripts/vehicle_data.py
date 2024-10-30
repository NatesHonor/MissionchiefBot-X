import json
import time
import configparser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from multiprocessing import Value

def gather_vehicle_data(driver, urls, thread_id, shared_vehicle_data, shared_lock, total_vehicles_fetched, total_vehicles):
    print(f"Thread {thread_id}: Gathering vehicle data...")
    vehicle_data = {}

    for current_vehicle_number, vehicle_url in enumerate(urls, start=1):
        with shared_lock:
            total_vehicles_fetched.value += 1
            current_total = total_vehicles_fetched.value
        print(f"Thread {thread_id}: Gathering data from vehicle {current_total}/{total_vehicles} {vehicle_url}")
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

    with shared_lock:
        shared_vehicle_data.update(vehicle_data)

    for vehicle_id, data in vehicle_data.items():
        print(f"Thread {thread_id}: Vehicle ID: {vehicle_id}, Name: {data['name']}")

def main():
    from scripts.logon import login

    config = configparser.ConfigParser()
    config.read('../config.ini')
    threads = int(config.get('client', 'thread_count'))

    shared_vehicle_data = {}
    shared_lock = Lock()
    total_vehicles_fetched = Value('i', 0)

    drivers = [login() for _ in range(threads)]

    with ThreadPoolExecutor(max_workers=threads) as executor:
        driver_vehicle_urls = [[] for _ in range(threads)]
        first_driver = drivers[0]
        first_driver.get('https://missionchief.com/leitstellenansicht')
        time.sleep(10)
        vehicle_urls = [link.get_attribute('href')
                        for link in first_driver.find_elements(By.CSS_SELECTOR,
                                                               'a.lightbox-open.list-group-item[href*="/vehicles/"]')]
        total_vehicles = len(vehicle_urls)
        print(f"All threads: Total vehicles found {total_vehicles}")

        futures = [executor.submit(gather_vehicle_data, driver, urls, thread_id, shared_vehicle_data, shared_lock, total_vehicles_fetched, total_vehicles)
                   for thread_id, (driver, urls) in enumerate(zip(drivers, driver_vehicle_urls))]

        for future in futures:
            future.result()

    with shared_lock:
        with open('data/vehicle_data.json', 'w') as vehicle_file:
            json.dump(shared_vehicle_data, vehicle_file)

if __name__ == "__main__":
    main()
