"""Compatibility API for the old region URL setup flow."""

from core.regions import get_region_profile

_profile = None


def setup_region(region=None):
    global _profile
    _profile = get_region_profile(region)
    return _profile.base_url


def get_url():
    return (_profile or get_region_profile()).base_url
