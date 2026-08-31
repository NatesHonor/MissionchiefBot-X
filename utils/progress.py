"""Progress reporting that remains readable in terminals and captured consoles."""

from __future__ import annotations

import sys
from threading import Lock

from .pretty_print import display_info


class ProgressBar:
    """Render aggregate progress without assuming an interactive terminal."""

    def __init__(self, label: str, total: int, width: int = 24):
        self.label = label
        self.total = max(0, int(total))
        self.width = max(8, int(width))
        self.current = 0
        self._lock = Lock()
        self._interactive = bool(getattr(sys.stdout, "isatty", lambda: False)())

    def _line(self, detail: str = "") -> str:
        completed = min(max(self.current, 0), self.total)
        percent = 100 if self.total == 0 else int(completed * 100 / self.total)
        filled = self.width if self.total == 0 else int(self.width * completed / self.total)
        bar = "#" * filled + "-" * (self.width - filled)
        suffix = f" | {detail}" if detail else ""
        return f"{self.label}: [{bar}] {completed}/{self.total} ({percent:3d}%){suffix}"

    def _render_locked(self, detail: str = "") -> None:
        line = self._line(detail)
        if self._interactive:
            print(f"\r{line}", end="", flush=True)
        else:
            display_info(line)

    def start(self, detail: str = "starting") -> None:
        with self._lock:
            self._render_locked(detail)

    def advance(self, detail: str = "") -> None:
        with self._lock:
            self.current = min(self.total, self.current + 1)
            self._render_locked(detail)

    def finish(self, detail: str = "complete") -> None:
        with self._lock:
            line = self._line(detail)
            if self._interactive:
                print(f"\r{line}", flush=True)
            else:
                display_info(line)
