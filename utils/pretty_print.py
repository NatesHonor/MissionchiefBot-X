"""Short logging helpers used across the bot."""

from __future__ import annotations

from core.logging_config import ensure_logging


def display_error(message: object) -> None:
    ensure_logging().error(str(message))


def display_warning(message: object) -> None:
    ensure_logging().warning(str(message))


def display_info(message: object) -> None:
    ensure_logging().info(str(message))
