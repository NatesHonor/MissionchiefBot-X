from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import art


_LOGGER_NAME = "missionchiefbot"
_DEFAULT_LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "missionchiefbot.log"


def _logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        configured_path = os.getenv("MISSIONCHIEF_LOG_FILE")
        destination = Path(configured_path).expanduser() if configured_path else _DEFAULT_LOG_FILE
        destination.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            destination,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(handler)
    except (OSError, ValueError):
        # Console output must remain available even when the log destination is
        # unavailable or misconfigured.
        logger.addHandler(logging.NullHandler())
    return logger

def display_message(message):
    ascii_art = art.text2art(message)
    print(ascii_art)
    _logger().info(str(message))

def display_error(message):
    print(f"\033[91m{message}\033[0m")
    _logger().error(str(message))

def display_warning(message):
    print(f"\033[93m{message}\033[0m")
    _logger().warning(str(message))

def display_info(message):
    print(f"{message}")
    _logger().info(str(message))
