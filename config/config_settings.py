"""Backward-compatible settings getters.

New code receives one :class:`core.settings.Settings` snapshot. These small
getters remain for older integrations that still import this module.
"""

import os

from core.settings import DEFAULT_CONFIG_PATH, get_settings

config_path = os.getenv("MISSIONCHIEF_CONFIG_FILE", str(DEFAULT_CONFIG_PATH))


def get_username():
    return get_settings().username


def get_password():
    return get_settings().password


def get_headless():
    return get_settings().headless


def get_threads():
    return get_settings().browsers


def get_browser_scaling():
    return get_settings().browser_scaling


def get_dispatch_type():
    return get_settings().dispatch_type


def get_dispatch_by_distance():
    return get_settings().dispatch_by_distance


def get_dispatch_incomplete():
    return get_settings().dispatch_incomplete


def get_dynamic_missions():
    return get_settings().dynamic_missions


def get_concurrent_missions():
    return get_settings().concurrent_missions


def get_auto_training():
    return get_settings().auto_training


def get_auto_recruiting():
    return get_settings().auto_recruiting


def get_auto_special_resources():
    return get_settings().auto_special_resources


def get_recruiting_days():
    return get_settings().recruiting_days


def get_auto_tasks():
    return get_settings().auto_tasks


def get_region():
    return get_settings().region


def delays_are_dynamic():
    return get_settings().dynamic_delays


def get_dynamic_delay_missions_enabled():
    return get_settings().dynamic_delay_missions


def get_dynamic_delay_transport_enabled():
    return get_settings().dynamic_delay_transport


def get_mission_delay():
    return get_settings().mission_delay


def get_other_delay():
    return get_settings().other_delay
