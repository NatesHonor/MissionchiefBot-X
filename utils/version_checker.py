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


def check_version():
    if beta == 'False':
        cprint(figlet_format(f'v{version}', font='5lineoblique'),
               'yellow', 'on_red', attrs=['bold'])
        response = requests.get('https://api.github.com/repos/NatesHonor/MissionchiefBot/releases/latest')
        latest_version = response.json()['tag_name']

        latest_version = latest_version.lstrip('v')

        if version != latest_version:
            logging.info(f"New version available! Please update to v{latest_version}"
                         f" for code improvements and better functionality!")
            logging.info("https://github.com/NatesHonor/MissionchiefBot/releases/latest")
    elif beta == 'True':
        cprint(figlet_format(f'This is a beta version!', font='5lineoblique'),
               'red', 'on_red', attrs=['bold'])
