import logging
import threading
import time
import math


from scripts.logon import login
from scripts.transport import transport_submit
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

calendar = config.getboolean('other', 'calendar', fallback=False)
claim_tasks_settings = config.getboolean('other', 'claim_tasks', fallback=False)
claim_tasks_time = config.getint('other', 'claim_tasks_time', fallback=0)
event_calendar = config.getboolean('other', 'event_calendar', fallback=False)
handletransportrequests = config.getboolean('transport', 'should_handle_transport_requests', fallback=False)
handletransportrequeststime = config.getint('transport', 'should_handle_transport_requests_time', fallback=0)


def settings():
    if handletransportrequests:
        def transport_loop():
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

