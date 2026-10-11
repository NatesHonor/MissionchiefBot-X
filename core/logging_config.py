"""Centralized, low-noise console and file logging."""

from __future__ import annotations

import logging
import re
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterable, Mapping

from rich.console import Console, Group
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


LOGGER_NAME = "missionchiefbot"
DEFAULT_LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "missionchiefbot.log"
_THREAD_MESSAGE = re.compile(r"^Thread (?P<thread>\d+):\s*(?P<message>.*)$")
_console = Console()
_configured = False


@dataclass
class ThreadState:
    message: str
    level: int
    updated_at: datetime
    repeats: int = 1


class ActivityConsoleHandler(logging.Handler):
    """Present thread activity as compact snapshots rather than duplicate lines."""

    def __init__(self, *, refresh_every: int = 3) -> None:
        super().__init__()
        self.refresh_every = max(1, refresh_every)
        self.thread_states: dict[str, ThreadState] = {}
        self.other_repeats: defaultdict[tuple[int, str], int] = defaultdict(int)
        self._events_since_snapshot = 0
        self._lock = threading.RLock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            match = _THREAD_MESSAGE.match(message)
            with self._lock:
                if match:
                    self._record_thread(match.group("thread"), match.group("message"), record.levelno)
                else:
                    self._record_event(message, record.levelno)
        except Exception:
            self.handleError(record)

    def _record_thread(self, thread_id: str, message: str, level: int) -> None:
        previous = self.thread_states.get(thread_id)
        repeats = previous.repeats + 1 if previous and previous.message == message else 1
        self.thread_states[thread_id] = ThreadState(message, level, datetime.now(), repeats)
        self._events_since_snapshot += 1
        if level >= logging.ERROR or self._events_since_snapshot >= self.refresh_every:
            self.render_snapshot()

    def _record_event(self, message: str, level: int) -> None:
        key = (level, message)
        self.other_repeats[key] += 1
        count = self.other_repeats[key]
        if count == 1 or level >= logging.WARNING:
            style = "bold red" if level >= logging.ERROR else "yellow" if level >= logging.WARNING else "cyan"
            suffix = f"  ×{count}" if count > 1 else ""
            _console.print(Text(f"{message}{suffix}", style=style))

    def render_snapshot(self) -> None:
        if not self.thread_states:
            return
        table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
        table.add_column("Worker", width=8)
        table.add_column("State", width=10)
        table.add_column("Latest activity", ratio=1)
        table.add_column("Updated", justify="right", width=10)
        for thread_id in sorted(self.thread_states, key=int):
            state = self.thread_states[thread_id]
            label, style = _level_label(state.level)
            message = state.message + (f"  ×{state.repeats}" if state.repeats > 1 else "")
            table.add_row(f"#{thread_id}", Text(label, style=style), message, state.updated_at.strftime("%H:%M:%S"))
        _console.print(Panel(table, title="MissionChief Bot · Worker activity", border_style="bright_black"))
        self._events_since_snapshot = 0


def _level_label(level: int) -> tuple[str, str]:
    if level >= logging.ERROR:
        return "FAILED", "bold red"
    if level >= logging.WARNING:
        return "WARNING", "yellow"
    return "ACTIVE", "green"


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(LOGGER_NAME if not name else f"{LOGGER_NAME}.{name}")


def configure_logging(
    *,
    level: str = "INFO",
    console_enabled: bool = True,
    file_enabled: bool = True,
    visual_console: bool = True,
    log_file: str | Path = DEFAULT_LOG_FILE,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Configure application logging once for both console and file output."""

    global _configured
    logger = get_logger()
    logger.handlers.clear()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    if console_enabled:
        if visual_console:
            logger.addHandler(ActivityConsoleHandler())
        else:
            handler = RichHandler(console=_console, show_path=False, rich_tracebacks=True, markup=False)
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)

    if file_enabled:
        destination = Path(log_file).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(destination, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(file_handler)

    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    _configured = True
    return logger


def ensure_logging() -> logging.Logger:
    return get_logger() if _configured else configure_logging()


def display_table(title: str, columns: Iterable[str], rows: Iterable[Iterable[Any]]) -> None:
    """Show structured console data and write the same information to the logfile."""

    logger = ensure_logging()
    headings = tuple(str(column) for column in columns)
    values = [tuple(str(value) for value in row) for row in rows]
    table = Table(title=title, header_style="bold cyan", border_style="bright_black")
    for heading in headings:
        table.add_column(heading)
    for row in values:
        table.add_row(*row)
    if any(isinstance(handler, ActivityConsoleHandler) for handler in logger.handlers):
        _console.print(table)
    logger.info("%s | %s", title, " | ".join(headings))
    for row in values:
        logger.info("%s | %s", title, " | ".join(row))


def display_summary(title: str, values: Mapping[str, Any]) -> None:
    display_table(title, ("Setting", "Value"), values.items())
