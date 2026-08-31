"""Backward-compatible US mission fan-out imports."""

from core.concurrency import split_mission_ids_among_threads

__all__ = ["split_mission_ids_among_threads"]
