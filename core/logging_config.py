"""Centralized console and rotating-file logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterable, Mapping

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table


LOGGER_NAME = "missionchiefbot"
DEFAULT_LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "missionchiefbot.log"
_console = Console()
_configured = False


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(LOGGER_NAME if not name else f"{LOGGER_NAME}.{name}")


def configure_logging(
    *,
    level: str = "INFO",
    console_enabled: bool = True,
    file_enabled: bool = True,
    rich_console: bool = True,
    log_file: str | Path = DEFAULT_LOG_FILE,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Configure the complete application logger and replace stale handlers."""

    global _configured
    logger = get_logger()
    logger.handlers.clear()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    if console_enabled:
        handler: logging.Handler
        if rich_console:
            handler = RichHandler(console=_console, show_path=False, rich_tracebacks=True, markup=False)
            handler.setFormatter(logging.Formatter("%(message)s"))
        else:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)

    if file_enabled:
        destination = Path(log_file).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            destination,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(file_handler)

    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    _configured = True
    return logger


def ensure_logging() -> logging.Logger:
    if not _configured:
        return configure_logging()
    return get_logger()


def log_table(title: str, columns: Iterable[str], rows: Iterable[Iterable[Any]]) -> None:
    """Render a table on rich consoles and record equivalent rows in the log file."""

    logger = ensure_logging()
    column_names = tuple(str(column) for column in columns)
    normalized_rows = [tuple(str(value) for value in row) for row in rows]
    if any(isinstance(handler, RichHandler) for handler in logger.handlers):
        table = Table(title=title)
        for column in column_names:
            table.add_column(column)
        for row in normalized_rows:
            table.add_row(*row)
        _console.print(table)
    logger.info("%s | %s", title, " | ".join(column_names))
    for row in normalized_rows:
        logger.info("%s | %s", title, " | ".join(row))


def log_mapping(title: str, values: Mapping[str, Any]) -> None:
    log_table(title, ("Setting", "Value"), values.items())
