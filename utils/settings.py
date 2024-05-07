import logging
import threading
import time

from scripts.logon import login
from scripts.transport import transport_submit
import os
import configparser

print(f"Current working directory: {os.getcwd()}")

# Check if the file exists
if os.path.exists('config.ini'):
    print("File exists.")
else:
    print("File does not exist.")

# Try to read the file
config = configparser.ConfigParser()
try:
    config.read('config.ini')
    print("File read successfully.")
except Exception as e:
    print(f"Error reading file: {e}")

config = configparser.ConfigParser()
config.read('config.ini')

calendar = config.getboolean('other', 'calendar', fallback=False)
claim_tasks = config.getboolean('other', 'claim_tasks', fallback=False)
solve_tasks = config.getboolean('other', 'solve_tasks', fallback=False)
event_calendar = config.getboolean('other', 'event_calendar', fallback=False)
handletransportrequests = config.getboolean('missions', 'should_handle_transport_requests', fallback=False)
handletransportrequeststime = config.getint('missions', 'should_handle_transport_requests_time', fallback=0)


def settings():
    if handletransportrequests:
        def transport_loop():
            time.sleep(10)
            transport_driver = login()
            while True:
                logging.info("Transporting prisoners and patients...")
                transport_submit(transport_driver)
                logging.info(f"Sleeping for {handletransportrequeststime} seconds...")
                time.sleep(handletransportrequeststime)

        transport_thread = threading.Thread(target=transport_loop)
        transport_thread.start()

    if calendar:
        driver1 = login()
        driver1.get('https://www.missionchief.com/daily_bonuses')
        driver1.quit()

    if event_calendar:
        driver2 = login()
        driver2.get('https://www.missionchief.com/event-calendar')
        driver2.quit()
        login()

    if claim_tasks:
        def claimtask_loop():
            time.sleep(300)
            claimtask_driver = login()
            while True:
                logging.info("...")
                transport_submit(claimtask_driver)
                logging.info("Sleeping for 5 minutes...")
                time.sleep(handletransportrequeststime)

        transport_thread = threading.Thread(target=claimtask_loop)
        transport_thread.start()

    if solve_tasks:
        def solvetask_loop():
            time.sleep(300)
            solvetask_driver = login()
            while True:
                logging.info("...")
                transport_submit(solvetask_driver)
                logging.info("Sleeping for 5 minutes...")
                time.sleep(handletransportrequeststime)

        transport_thread = threading.Thread(target=solvetask_loop)
        transport_thread.start()
