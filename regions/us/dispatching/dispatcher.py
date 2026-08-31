"""Backward-compatible US dispatch imports."""

from core.dispatching.dispatcher import (
    handle_water_requirement,
    navigate_and_dispatch,
    read_water_status,
)

__all__ = ["handle_water_requirement", "navigate_and_dispatch", "read_water_status"]
