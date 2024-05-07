import time
import json
import os
import configparser
import logging

from data.vehicle_mapping import vehicle_map
from data.personnel_mapping import personnel_map

from scripts.logon import login
from scripts.clean import mission_cleaner
from scripts.vehicle_data import gather_vehicle_data
from scripts.missions.mission_data import gather_mission_data
from scripts.gather_missions import total_number_of_missions
from scripts.dispatch.dispatcher import dispatch_vehicles
from utils.version_checker import check_version
from utils.settings import settings

logging.basicConfig(level=logging.INFO)

check_version()
driver = login()
config = configparser.ConfigParser()
config.read('config.ini')

vehicle_dispatch_mapping = vehicle_map
personnel_dispatch_mapping = personnel_map


if os.path.exists('data/vehicle_data.json'):
    logging.info("Since vehicle_data.json exists we will just use the existing vehicle data!")
else:
    logging.info("Gathering vehicle data...")
    gather_vehicle_data(driver)

with open('data/vehicle_data.json', 'r') as f:
    vehicle_data = json.load(f)

logging.info("Applying settings!")
settings()
with open('data/vehicle_data.json', 'r') as f:
    vehicle_pool = json.load(f)

while True:
    logging.info("Gathering total number of missions...")
    mission_numbers = total_number_of_missions(driver)

    logging.info("Gathering mission data...")
    missions_data = gather_mission_data(driver, mission_numbers)

    with open('data/missions_data.json', 'w') as f:
        json.dump(missions_data, f)

    for m_number, mission_info in missions_data.items():
        missionsleep = config.getboolean('missions', 'should_wait_before_missions', fallback=False)
        missionsleeptime = config.getint('missions', 'should_wait_before_missions_time', fallback=False)
        if missionsleep:
            time.sleep(missionsleeptime)
        try:
            mission_requirements = mission_info['vehicles']
            max_patients = mission_info.get('patients', 0)
            crashed_cars = mission_info.get('crashed_cars', 0)
            prisoners = mission_info.get('prisoners', 0)
            logging.info(f"Dispatching vehicles for mission {m_number}")
            dispatch_vehicles(driver, m_number, vehicle_pool, mission_requirements, max_patients,
                              vehicle_dispatch_mapping, crashed_cars, 'data/missions_data.json',
                              prisoners, personnel_dispatch_mapping)

        except KeyError as e:
            logging.error(f"Error processing mission {m_number}: {e}")
    logging.info("Completed all basic mission dispatches!")

    logging.info("Now attempting to clean up missions")
    for m_number in mission_numbers:
        mission_cleaner(driver, m_number)
