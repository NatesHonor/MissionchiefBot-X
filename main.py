import time
import json
import os
import configparser
import logging
from concurrent.futures import ThreadPoolExecutor

from selenium.webdriver.common.by import By
from threading import Lock

from data.vehicle_mapping import vehicle_map
from data.personnel_mapping import personnel_map
from functions import gather_missions, setup_driver

from scripts.gather_missions import total_number_of_missions
from scripts.dispatch.dispatcher import dispatch_vehicles
from scripts.vehicle_data import gather_vehicle_data
from utils.tables.maintables import display_final_table, display_missions_data, display_mission_table
from utils.version_checker import check_version
from utils.settings import settings
from scripts.missions.transport_needed import check_transport_needed

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

check_version()
config = configparser.ConfigParser()

config.read('config.ini')

threads = config.getint('client', 'threads', fallback=1)
print("Logging into threads")


logging.info("Applying settings!")
settings()
def dispatch_all_missions(driver):
    vehicle_dispatch_mapping = vehicle_map
    personnel_dispatch_mapping = personnel_map

    with open('data/vehicle_data.json', 'r') as vehicle_file:
        vehicle_pool = json.load(vehicle_file)



    for m_number, mission_info in shared_missions_data.items():
        display_mission_table(shared_missions_data, m_number)

        missionsleep = config.getboolean('missions', 'should_wait_before_missions', fallback=False)
        missionsleeptime = config.getint('missions', 'should_wait_before_missions_time', fallback=False)
        if missionsleep:
            time.sleep(missionsleeptime)
        check_transport_needed(driver)
        try:
            mission_requirements = mission_info['vehicles']
            crashed_cars = mission_info.get('crashed_cars', 0)
            prisoners = mission_info.get('prisoners', 0)
            dispatch_vehicles(driver, m_number, vehicle_pool, mission_requirements,
                              vehicle_dispatch_mapping, crashed_cars, 'data/missions_data.json',
                              prisoners, personnel_dispatch_mapping)

        except KeyError as e:
            logging.error(f"Error processing mission {m_number}: {e}")
        except TypeError as e:
            logging.error(f"TypeError processing mission {m_number}: {e}")
    logging.info("Completed all basic mission dispatches!")

if __name__ == "__main__":
    shared_vehicle_data = {}
    shared_missions_data = {}
    shared_lock = Lock()

    drivers = [setup_driver() for _ in range(threads)]

    if not os.path.exists('data/vehicle_data.json'):
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
            with open('data/vehicle_data.json', 'w') as vehiclesfile:
                json.dump(shared_vehicle_data, vehiclesfile)

    while True:
        shared_missions_data.clear()
        first_driver = drivers[0]
        total_missions = total_number_of_missions(first_driver)
        total_missions_count = len(total_missions)
        missions_per_thread = total_missions_count // threads
        extra_missions = total_missions_count % threads

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            start = 0
            for thread_id, driver in enumerate(drivers):
                end = start + missions_per_thread + (1 if thread_id < extra_missions else 0)
                mission_numbers = total_missions[start:end]
                futures.append(executor.submit(gather_missions, driver, thread_id, mission_numbers, shared_missions_data, shared_lock))
                start = end

            for future in futures:
                future.result()

        with shared_lock:
            with open('data/missions_data.json', 'w') as missions_file:
                json.dump(shared_missions_data, missions_file)
        display_missions_data(shared_missions_data)
        dispatch_all_missions(drivers[0])
        display_final_table(shared_missions_data)
