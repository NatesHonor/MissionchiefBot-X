import configparser
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(parent_dir, 'config.ini')
config = configparser.ConfigParser()
config.read(config_path)

# -----------------------------
# Credentials
# -----------------------------
def get_username():
    return config.get('credentials', 'username')

def get_password():
    return config.get('credentials', 'password')


# -----------------------------
# Browser Settings
# -----------------------------
def get_headless():
    return config.getboolean('browser_settings', 'headless')

def get_threads():
    return config.getint('browser_settings', 'browsers')

def get_browser_scaling():
    return config.getboolean('browser_settings', 'browser_scaling')


# -----------------------------
# Mission Settings
# -----------------------------
def get_dispatch_type():
    return config.get('missions', 'dispatch')

def get_dispatch_by_distance():
    return config.getboolean('missions', 'dispatch_vehicles_by_distance')

def get_dispatch_incomplete():
    return config.getboolean('missions', 'dispatch_incomplete_missions')

def get_dynamic_missions():
    return config.getboolean('missions', 'dynamic_missions')

def get_concurrent_missions():
    return config.getboolean('missions', 'dispatch_concurrent_missions')

# -----------------------------
# Other Settings
# -----------------------------
def get_auto_training():
    return config.getboolean('other', 'auto_training')


# -----------------------------
# Delays & Dynamic Settings
# -----------------------------
def delays_are_dynamic():
    return config.getboolean('delays', 'dynamic_delays')

def get_dynamic_delay_missions_enabled():
    return config.getboolean('delays', 'dynamic_missions')

def get_dynamic_delay_transport_enabled():
    return config.getboolean('delays', 'dynamic_transport')

def get_mission_delay():
    return config.getint('delays', 'missions')

def get_transport_delay():
    return config.getint('delays', 'transport')
