"""Startup update check.

Before the bot starts, compare the installed version with the latest GitHub
release. When a newer release exists, show a notice with a short summary of
the changes and ask whether to update now:

* ``y`` downloads the release, installs it over this copy, migrates the
  ``.env`` settings to the new version, updates dependencies and restarts.
* ``n`` (or just Enter) starts the current version as normal.

If nobody can answer (no terminal attached, e.g. the launcher or a service),
the notice is shown and the bot starts without asking. Set
``MISSIONCHIEF_AUTO_UPDATE=true`` to install updates without a prompt.

The check never stops the bot: no network, a GitHub error, an unreadable
version or a failed update just carries on with the installed version. Set
``MISSIONCHIEF_UPDATE_CHECK=false`` to turn it off.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv

from core.auto_updater import UpdateError, can_self_update, perform_update

REPOSITORY = "NatesHonor/MissionchiefBot-X"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
MANIFEST = Path(__file__).resolve().parent.parent / ".release-please-manifest.json"
MAX_SUMMARY_LINES = 8
_FALSE = {"0", "false", "no", "off"}
_TRUE = {"1", "true", "yes", "on"}


def parse_version(value: object) -> tuple[int, int, int] | None:
    """Turn ``"v3.3.1"`` or ``"3.3.1"`` into ``(3, 3, 1)``."""

    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(value or ""))
    if not match:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def current_version(manifest: Path = MANIFEST) -> str | None:
    """The installed version, from Release Please's manifest."""

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    version = data.get(".") if isinstance(data, dict) else None
    return str(version) if version else None


def fetch_latest_release(timeout: float = 4.0) -> dict | None:
    """The latest published GitHub release, or ``None`` if it can't be read."""

    request = urllib.request.Request(
        LATEST_RELEASE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "MissionchiefBot-X-update-check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310 - fixed HTTPS URL
            release = json.load(response)
    except Exception:
        return None
    return release if isinstance(release, dict) else None


def summarize_changes(body: object, limit: int = MAX_SUMMARY_LINES) -> list[str]:
    """Pull the change bullets out of a Release Please changelog.

    Commit hashes, issue links and Markdown are removed so each line reads
    as plain text.
    """

    lines = []
    for raw in str(body or "").splitlines():
        line = raw.strip()
        if not re.match(r"^[*-]\s+", line):
            continue
        line = re.sub(r"^[*-]\s+", "", line)
        line = re.sub(r"\s*\(\[[0-9a-f]{7,40}\]\([^)]*\)\)", "", line)
        line = re.sub(r"\s*\(\[#\d+\]\([^)]*\)\)", "", line)
        line = re.sub(r",?\s*closes\s+\[#\d+\]\([^)]*\)", "", line, flags=re.I)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = line.replace("**", "").strip()
        if line:
            lines.append(line)
    if len(lines) > limit:
        hidden = len(lines) - limit
        lines = [*lines[:limit], f"...and {hidden} more"]
    return lines


def newer_release(installed: object, release: dict | None) -> dict | None:
    """Return the release when it is newer than the installed version."""

    if not release or release.get("draft") or release.get("prerelease"):
        return None
    installed_version = parse_version(installed)
    latest_version = parse_version(release.get("tag_name"))
    if not installed_version or not latest_version or latest_version <= installed_version:
        return None
    return release


def _show_notice(installed: str, release: dict, footer: str) -> None:
    latest = str(release.get("tag_name") or "").lstrip("v")
    url = release.get("html_url") or RELEASES_URL
    changes = summarize_changes(release.get("body"))
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        text = Text()
        text.append("A new version of MissionchiefBot-X is available!\n\n", style="bold")
        text.append(f"  {installed}", style="red")
        text.append("  ->  ")
        text.append(f"{latest}\n\n", style="bold green")
        if changes:
            text.append("What's new:\n", style="bold")
            for change in changes:
                text.append(f"  • {change}\n")
            text.append("\n")
        text.append("Release notes: ", style="bold")
        text.append(url, style=f"underline cyan link {url}")
        if footer:
            text.append(f"\n\n{footer}", style="dim")
        Console().print(Panel(text, title="Update available", border_style="yellow", padding=(1, 2)))
    except Exception:
        print(f"\n=== Update available: {installed} -> {latest} ===")
        for change in changes:
            print(f"  - {change}")
        print(f"Release notes: {url}")
        if footer:
            print(footer)
        print()


def _interactive() -> bool:
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def ask_yes_no(question: str, read: Callable[[str], str] = input) -> bool:
    """Ask a y/n question; anything but yes (including Enter or Ctrl+D) is no."""

    while True:
        try:
            answer = read(f"{question} [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if answer in {"y", "yes"}:
            return True
        if answer in {"", "n", "no"}:
            return False
        print("Please answer y or n.")


def check_for_updates(
    read: Callable[[str], str] = input,
    interactive: Callable[[], bool] = _interactive,
    update: Callable[..., None] = perform_update,
) -> bool:
    """Offer to install a newer release.

    Returns ``True`` only when an update was installed, so the caller should
    restart into the new version. Every other outcome returns ``False`` and
    the current version keeps running.
    """

    with contextlib.suppress(Exception):
        load_dotenv()
    if os.environ.get("MISSIONCHIEF_UPDATE_CHECK", "true").strip().lower() in _FALSE:
        return False
    try:
        installed = current_version()
        if not installed:
            return False
        release = newer_release(installed, fetch_latest_release())
        if not release:
            return False

        blocked = can_self_update()
        automatic = os.environ.get("MISSIONCHIEF_AUTO_UPDATE", "false").strip().lower() in _TRUE
        if blocked:
            _show_notice(installed, release, f"Automatic update unavailable: {blocked}\nStarting the current version...")
            return False
        if automatic:
            _show_notice(installed, release, "MISSIONCHIEF_AUTO_UPDATE is on, installing the update...")
        elif interactive():
            _show_notice(installed, release, "")
            if not ask_yes_no("Update now? Your settings (.env) will be carried over.", read):
                print("Skipping the update. Starting the current version...\n")
                return False
        else:
            _show_notice(installed, release, "Starting the current version...")
            return False
    except Exception:
        return False

    try:
        update(release, installed)
    except UpdateError as error:
        print(f"\nUpdate failed: {error}\nStarting the current version...\n")
        return False
    except Exception as error:
        print(f"\nUpdate failed unexpectedly: {error}\nStarting the current version...\n")
        return False
    print("\nUpdate complete. Restarting...\n")
    return True
