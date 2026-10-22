"""Centralized, low-noise console and file logging."""

from __future__ import annotations

import atexit
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
_visual_handler: VisualConsoleHandler | None = None


@dataclass
class Activity:
    message: str
    level: int
    updated_at: datetime
    repeats: int = 1


class VisualConsoleHandler(logging.Handler):
    """Render all runtime output through one compact visual language."""

    def __init__(self, *, snapshot_every: int = 4) -> None:
        super().__init__()
        self.snapshot_every = max(1, snapshot_every)
        self.workers: dict[str, Activity] = {}
        self.events: list[Activity] = []
        self.repeats: defaultdict[tuple[int, str], int] = defaultdict(int)
        self._updates = 0
        self._lock = threading.RLock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage().strip()
            if not message:
                return
            with self._lock:
                match = _THREAD_MESSAGE.match(message)
                if match:
                    self._worker(match.group("thread"), match.group("message"), record.levelno)
                else:
                    self._event(message, record.levelno)
        except Exception:
            self.handleError(record)

    def _worker(self, worker: str, message: str, level: int) -> None:
        previous = self.workers.get(worker)
        repeats = previous.repeats + 1 if previous and previous.message == message else 1
        self.workers[worker] = Activity(message, level, datetime.now(), repeats)
        self._updates += 1
        if level >= logging.ERROR or self._updates >= self.snapshot_every:
            self.snapshot()

    def _event(self, message: str, level: int) -> None:
        key = (level, message)
        self.repeats[key] += 1
        count = self.repeats[key]
        if count > 1 and level < logging.WARNING:
            return
        self.events.append(Activity(message, level, datetime.now(), count))
        self.events = self.events[-5:]
        if level >= logging.WARNING:
            self.alert(message, level, count)
        elif not self.workers:
            self.status(message, level)

    def status(self, message: str, level: int = logging.INFO) -> None:
        label, style = _level_style(level)
        _console.print(Panel(Text(message, style=style), title=f"MissionChief Bot · {label}", border_style=style))

    def alert(self, message: str, level: int, repeats: int = 1) -> None:
        label, style = _level_style(level)
        suffix = f"\nRepeated {repeats} times" if repeats > 1 else ""
        _console.print(Panel(Text(f"{message}{suffix}", style=style), title=label, border_style=style))

    def snapshot(self, *, title: str = "Worker activity") -> None:
        if not self.workers:
            return
        table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2), expand=True)
        table.add_column("Worker", width=8)
        table.add_column("State", width=10)
        table.add_column("Latest activity", ratio=1)
        table.add_column("Updated", justify="right", width=10)
        for worker in sorted(self.workers, key=int):
            activity = self.workers[worker]
            label, style = _level_style(activity.level)
            message = activity.message + (f"  ×{activity.repeats}" if activity.repeats > 1 else "")
            table.add_row(f"#{worker}", Text(label, style=style), message, activity.updated_at.strftime("%H:%M:%S"))
        footer = Text("Detailed history: logs/missionchiefbot.log", style="dim")
        _console.print(Panel(Group(table, footer), title=f"MissionChief Bot · {title}", border_style="bright_black"))
        self._updates = 0

    def session_summary(self) -> None:
        if not self.workers and not self.events:
            return
        failed = sum(activity.level >= logging.ERROR for activity in self.workers.values())
        warning = sum(activity.level == logging.WARNING for activity in self.workers.values())
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row("Workers observed", str(len(self.workers)))
        table.add_row("Failed workers", str(failed))
        table.add_row("Workers with warnings", str(warning))
        table.add_row("Recorded event types", str(len(self.repeats)))
        _console.print(Panel(table, title="MissionChief Bot · Session summary", border_style="cyan"))


def _level_style(level: int) -> tuple[str, str]:
    if level >= logging.CRITICAL:
        return "FATAL", "bold white on red"
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
    global _configured, _visual_handler
    logger = get_logger()
    for old_handler in logger.handlers[:]:
        logger.removeHandler(old_handler)
        old_handler.close()
    _visual_handler = None
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    if console_enabled:
        if visual_console:
            _visual_handler = VisualConsoleHandler()
            logger.addHandler(_visual_handler)
        else:
            handler = RichHandler(console=_console, show_path=False, rich_tracebacks=True, markup=False)
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)

    if file_enabled:
        destination = Path(log_file).expanduser()
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(destination, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        except OSError as error:
            # A read-only disk should not prevent the bot from starting. The
            # console still reports the problem and continues without a file.
            _console.print(f"[yellow]File logging unavailable:[/yellow] {error}")
        else:
            file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
            logger.addHandler(file_handler)

    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    _configured = True
    return logger


def ensure_logging() -> logging.Logger:
    """Return the configured logger without opening a file on first use.

    The main application calls ``configure_logging`` with the user's settings.
    During imports and tests, an incidental log message should not create a
    rotating file handler (or fail because the log directory is read-only).
    """

    logger = get_logger()
    if not _configured and not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def display_header(subtitle: str, details: Mapping[str, Any] | None = None) -> None:
    title = Text("MISSIONCHIEF BOT", style="bold cyan")
    copy = [title, Text(subtitle, style="white")]
    if details:
        copy.append(Text("  ·  ".join(f"{key}: {value}" for key, value in details.items()), style="dim"))
    _console.print(Panel(Group(*copy), border_style="cyan", padding=(1, 2)))


def display_table(title: str, columns: Iterable[str], rows: Iterable[Iterable[Any]]) -> None:
    logger = ensure_logging()
    headings = tuple(str(column) for column in columns)
    values = [tuple(str(value) for value in row) for row in rows]
    table = Table(title=title, header_style="bold cyan", border_style="bright_black", expand=True)
    for heading in headings:
        table.add_column(heading)
    for row in values:
        table.add_row(*row)
    if _visual_handler:
        _console.print(table)
    logger.info("%s | %s", title, " | ".join(headings))
    for row in values:
        logger.info("%s | %s", title, " | ".join(row))


def display_summary(title: str, values: Mapping[str, Any]) -> None:
    display_table(title, ("Setting", "Value"), values.items())


def display_progress(label: str, completed: int, total: int) -> None:
    total = max(total, 1)
    completed = min(max(completed, 0), total)
    width = 24
    filled = round(width * completed / total)
    bar = f"[{'━' * filled}{'─' * (width - filled)}] {completed}/{total}"
    ensure_logging().info("%s %s", label, bar)


def flush_visual_summary() -> None:
    if _visual_handler:
        _visual_handler.snapshot(title="Final worker state")
        _visual_handler.session_summary()


atexit.register(flush_visual_summary)
