from colorama import init
from termcolor import cprint
from pyfiglet import figlet_format
import requests
import logging
import sys
import configparser
import json

with open('data/bot_info.json', 'r') as t:
    botdata = json.load(t)

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('config.ini')
beta = botdata.get('Beta')
version = botdata.get('Version')

init(strip=not sys.stdout.isatty())
print("Allow up to 50s for us to get everything ready!")
def check_version():
    if beta == 'False':
        cprint(figlet_format(f'v{version}', font='5lineoblique'), 'yellow', 'on_red', attrs=['bold'])
        try:
            response = requests.get('https://api.natemarcellus.com/version/missionchief')
            response.raise_for_status()
            latest_version = response.json().get('version')

            if latest_version and version != latest_version:
                logging.info(f"New version available! Please update to v{latest_version} "
                             f"for code improvements and better functionality!")
                logging.info("https://github.com/NatesHonor/MissionchiefBot/releases/latest")
            elif not latest_version:
                logging.error("Failed to retrieve the latest version from the API.")

        except requests.RequestException as e:
            logging.error(f"Error fetching version from the API: {e}")

    elif beta == 'True':
        cprint(figlet_format(f'This is a beta version!', font='5lineoblique'), 'red', 'on_red', attrs=['bold'])

check_version()
