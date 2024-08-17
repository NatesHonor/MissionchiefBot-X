import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchElementException
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

def gather_vehicle_data(driver, urls, thread_id, shared_vehicle_data, shared_lock):
    print(f"Thread {thread_id}: Gathering vehicle data...")
    vehicle_data = {}

    total_vehicles = len(urls)
    print(f"Thread {thread_id}: Found {total_vehicles} vehicles!")

    for current_vehicle_number, vehicle_url in enumerate(urls, start=1):
        print(f"Thread {thread_id}: Gathering data from vehicle {current_vehicle_number}/{total_vehicles} {vehicle_url}")
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

    shared_vehicle_data = {}
    shared_lock = Lock()
    threads = 4  # Number of threads to use

    drivers = [login() for _ in range(threads)]

    with ThreadPoolExecutor(max_workers=threads) as executor:
        driver_vehicle_urls = [[] for _ in range(threads)]
        first_driver = drivers[0]
        first_driver.get('https://missionchief.com/leitstellenansicht')
        time.sleep(10)
        vehicle_urls = [link.get_attribute('href')
                        for link in first_driver.find_elements(By.CSS_SELECTOR,
                                                               'a.lightbox-open.list-group-item[href*="/vehicles/"]')]
        for i, vehicle_url in enumerate(vehicle_urls):
            driver_vehicle_urls[i % threads].append(vehicle_url)

        futures = [executor.submit(gather_vehicle_data, driver, urls, thread_id, shared_vehicle_data, shared_lock)
                   for thread_id, (driver, urls) in enumerate(zip(drivers, driver_vehicle_urls))]

        for future in futures:
            future.result()

    with shared_lock:
        with open('data/vehicle_data.json', 'w') as vehicle_file:
            json.dump(shared_vehicle_data, vehicle_file)

if __name__ == "__main__":
    main()
