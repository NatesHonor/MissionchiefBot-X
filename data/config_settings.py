import configparser
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(parent_dir, 'config.ini')
config = configparser.ConfigParser()
config.read(config_path)

def get_username():
    return config.get('credentials', 'username')

def get_password():
    return config.get('credentials', 'password')

def get_headless():
    if config.getboolean('browser_settings', 'headless'):
        return True
    else:
        return False



def get_threads():
    return config.getint('browser_settings', 'threads')
