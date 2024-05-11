import logging
import threading
import time
import math


from scripts.logon import login
from scripts.transport import transport_submit
from scripts.other.task_manager import claim_tasks
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

calendar = config.getboolean('other', 'calendar', fallback=False)
claim_tasks_settings = config.getboolean('other', 'claim_tasks', fallback=False)
event_calendar = config.getboolean('other', 'event_calendar', fallback=False)
handletransportrequests = config.getboolean('transport', 'should_handle_transport_requests', fallback=False)
handletransportrequeststime = config.getint('transport', 'should_handle_transport_requests_time', fallback=0)


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

    if claim_tasks_settings:
        def claimtask_loop():
            claimtask_driver = login()
            while True:
                claim_tasks(claimtask_driver)
                time1 = math.ceil(1800 / 60)
                logging.info(f"Sleeping for {time1} minutes...")
                time.sleep(1800)
                time.sleep(handletransportrequeststime)

        transport_thread = threading.Thread(target=claimtask_loop)
        transport_thread.start()
