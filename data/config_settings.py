import configparser
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(parent_dir, 'config.ini')
config = configparser.ConfigParser()
config.read(config_path)

# Grabbing Credentials (for my reference)

def get_username():
    return config.get('credentials', 'username')

def get_password():
    return config.get('credentials', 'password')

# Grabbing Browser Settings (for my reference)

def get_headless():
    return config.getboolean('browser_settings', 'headless')

def get_threads():
    return config.getint('browser_settings', 'browsers')

# Grabbing Delays (for my reference)

def get_mission_delay():
    return config.getint('delays', 'missions')

def get_transport_delay():
    return config.getint('delays', 'transport')
