from __future__ import annotations

from core.logging_config import display_progress, ensure_logging


class ProgressDisplay:
    """Low-noise progress reporting through the centralized logging system."""

    def __init__(self, label: str, total: int, *, width: int = 20) -> None:
        self.label = label
        self.total = max(total, 1)
        self.width = width
        self.completed = 0
        self._last_reported = -1

    def start(self) -> ProgressDisplay:
        """Start reporting and support the legacy ProgressBar lifecycle."""
        ensure_logging().info("%s started", self.label)
        return self

    def update(self, completed: int, message: str | None = None) -> None:
        self.completed = min(max(completed, 0), self.total)
        percentage = round(self.completed * 100 / self.total)
        milestone = percentage // 10
        if milestone == self._last_reported and self.completed < self.total:
            return
        self._last_reported = milestone
        display_progress(message or self.label, self.completed, self.total)

    def finish(self, message: str | None = None) -> None:
        self.update(self.total, message or f"{self.label} complete")

    def __enter__(self) -> ProgressDisplay:
        return self.start()

    def __exit__(self, exc_type, exc, traceback) -> None:
        if exc is None:
            self.finish()
        else:
            ensure_logging().error("%s failed: %s", self.label, exc)
