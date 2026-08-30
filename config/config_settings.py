import configparser
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.getenv('MISSIONCHIEF_CONFIG_FILE', os.path.join(parent_dir, 'config.ini'))
config = configparser.ConfigParser()
config.read(config_path)


def _get_value(section, option, environment_name):
    """Read an environment override, then fall back to config.ini."""
    environment_value = os.getenv(environment_name)
    if environment_value is not None:
        return environment_value

    try:
        return config.get(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError) as error:
        raise RuntimeError(
            f"Missing configuration value [{section}] {option}. "
            f"Set {environment_name} or add it to {config_path}."
        ) from error


def _get_required_value(section, option, environment_name):
    value = _get_value(section, option, environment_name)
    if not value.strip():
        raise RuntimeError(f"{environment_name} must not be empty.")
    return value


def _get_boolean(section, option, environment_name):
    value = _get_value(section, option, environment_name).strip().lower()
    if value in {'1', 'yes', 'true', 'on'}:
        return True
    if value in {'0', 'no', 'false', 'off'}:
        return False
    raise ValueError(
        f"Invalid boolean value for {environment_name}: {value!r}. "
        "Use true/false."
    )


def _get_integer(section, option, environment_name):
    value = _get_value(section, option, environment_name).strip()
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"Invalid integer value for {environment_name}: {value!r}.") from error

# -----------------------------
# Credentials
# -----------------------------
def get_username():
    return _get_required_value('credentials', 'username', 'MISSIONCHIEF_USERNAME')

def get_password():
    return _get_required_value('credentials', 'password', 'MISSIONCHIEF_PASSWORD')


# -----------------------------
# Browser Settings
# -----------------------------
def get_headless():
    return _get_boolean('browser_settings', 'headless', 'MISSIONCHIEF_HEADLESS')

def get_threads():
    return _get_integer('browser_settings', 'browsers', 'MISSIONCHIEF_BROWSERS')

def get_browser_scaling():
    return _get_boolean(
        'browser_settings',
        'browser_scaling',
        'MISSIONCHIEF_BROWSER_SCALING'
    )


# -----------------------------
# Mission Settings
# -----------------------------
def get_dispatch_type():
    return _get_value('missions', 'dispatch', 'MISSIONCHIEF_DISPATCH')

def get_dispatch_by_distance():
    return _get_boolean(
        'missions',
        'dispatch_vehicles_by_distance',
        'MISSIONCHIEF_DISPATCH_VEHICLES_BY_DISTANCE'
    )

def get_dispatch_incomplete():
    return _get_boolean(
        'missions',
        'dispatch_incomplete_missions',
        'MISSIONCHIEF_DISPATCH_INCOMPLETE_MISSIONS'
    )

def get_dynamic_missions():
    return _get_boolean('missions', 'dynamic_missions', 'MISSIONCHIEF_DYNAMIC_MISSIONS')

def get_concurrent_missions():
    return _get_boolean(
        'missions',
        'dispatch_concurrent_missions',
        'MISSIONCHIEF_DISPATCH_CONCURRENT_MISSIONS'
    )

# -----------------------------
# Other Settings
# -----------------------------
def get_auto_training():
    return _get_boolean('other', 'auto_training', 'MISSIONCHIEF_AUTO_TRAINING')

def get_auto_tasks():
    return _get_boolean('other', 'auto_tasks', 'MISSIONCHIEF_AUTO_TASKS')

def get_region():
    return _get_value('bot', 'region', 'MISSIONCHIEF_REGION')


# -----------------------------
# Delays & Dynamic Settings
# -----------------------------
def delays_are_dynamic():
    return _get_boolean('delays', 'dynamic_delays', 'MISSIONCHIEF_DYNAMIC_DELAYS')

def get_dynamic_delay_missions_enabled():
    return _get_boolean(
        'delays',
        'dynamic_missions',
        'MISSIONCHIEF_DYNAMIC_DELAY_MISSIONS'
    )

def get_dynamic_delay_transport_enabled():
    return _get_boolean(
        'delays',
        'dynamic_transport',
        'MISSIONCHIEF_DYNAMIC_DELAY_TRANSPORT'
    )

def get_mission_delay():
    return _get_integer('delays', 'missions', 'MISSIONCHIEF_MISSION_DELAY')

def get_other_delay():
    return _get_integer('delays', 'other', 'MISSIONCHIEF_OTHER_DELAY')
