from __future__ import annotations

import art

from core.logging_config import ensure_logging
from core.logging_config import ensure_logging


def display_message(message):
    logger = ensure_logging()
    logger.info("\n%s", art.text2art(str(message)))


def display_error(message):
    ensure_logging().error(str(message))
    ensure_logging().error(str(message))


def display_warning(message):
    ensure_logging().warning(str(message))
    ensure_logging().warning(str(message))


def display_info(message):
    ensure_logging().info(str(message))
    ensure_logging().info(str(message))
