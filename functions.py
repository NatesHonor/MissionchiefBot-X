import logging

from scripts.logon import login
from scripts.missions.mission_data import gather_mission_data

def setup_driver():
    return login()

def gather_missions(driver, thread_id, mission_numbers, shared_missions_data, shared_lock):
    logging.info(f"Thread {thread_id}: Gathering mission data...")
    missions_data = gather_mission_data(driver, mission_numbers)

    with shared_lock:
        shared_missions_data.update(missions_data)