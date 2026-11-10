"""Install a newer GitHub release in place and migrate the user's settings.

The update runs in these steps:

1. Download the release zip from GitHub and unpack it into a temporary folder.
2. Back up the current install to ``.update-backup/<old-version>/``.
3. Copy the new files over the install. User data is never touched: ``.env``,
   ``config.ini``, ``.venv``, ``logs`` and the SQLite databases are kept.
4. Migrate ``.env`` against the new ``.env.example``. Every value the user
   set is kept, new settings are added with their defaults, and settings the
   new version no longer knows about are kept at the bottom of the file.
5. Reinstall the Python requirements and Playwright Chromium.

If any step before the dependency install fails, the backup is restored, so
a failed update leaves the bot as it was.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404 - runs pip/playwright with fixed arguments
import sys
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR_NAME = ".update-backup"
VERSION_KEY = "MISSIONCHIEF_VERSION"

# Top-level names that belong to the user or the local machine, not the release.
PRESERVED_NAMES = frozenset(
    {".env", "config.ini", ".venv", "venv", "logs", ".git", ".idea", ".vscode", BACKUP_DIR_NAME, "__pycache__"}
)
PRESERVED_SUFFIXES = (".sqlite3", ".sqlite3-journal", ".sqlite3-wal", ".sqlite3-shm", ".log")

_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")

Log = Callable[[str], object]


class UpdateError(RuntimeError):
    """The update could not be installed. The bot is left as it was."""


def in_docker() -> bool:
    return Path("/.dockerenv").exists() or bool(os.environ.get("MISSIONCHIEF_IN_DOCKER"))


def can_self_update(root: Path = PROJECT_ROOT) -> str | None:
    """Return why this install can't update itself, or ``None`` if it can."""

    if in_docker():
        return "Running in Docker. Pull the new image instead: docker compose pull && docker compose up -d"
    if (root / ".git").exists():
        return "This is a git checkout. Update with: git pull"
    if not os.access(root, os.W_OK):
        return f"No write access to {root}."
    return None


# --------------------------------------------------------------------------- #
# .env migration
# --------------------------------------------------------------------------- #


def parse_env(text: str) -> dict[str, str]:
    """Read ``KEY=value`` pairs, keeping each value exactly as written."""

    values: dict[str, str] = {}
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        match = _ENV_LINE.match(line)
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def migrate_env(old_env: str, template: str, new_version: str | None = None) -> str:
    """Build the new ``.env`` from the new template and the user's old values.

    The template sets the layout, comments and defaults. Any key the user
    already had keeps its value. Keys the template doesn't have are added
    at the end so nothing the user set is lost.
    """

    user = parse_env(old_env)
    used: set[str] = set()
    lines: list[str] = []
    for line in template.splitlines():
        match = None if line.lstrip().startswith("#") else _ENV_LINE.match(line)
        if not match:
            lines.append(line)
            continue
        key = match.group(1)
        if key == VERSION_KEY and new_version:
            value = new_version
        elif key in user:
            value = user[key]
        else:
            value = match.group(2).strip()
        used.add(key)
        lines.append(f"{key}={value}")

    leftovers = [key for key in user if key not in used]
    if leftovers:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("# Kept from your previous settings (not in the new .env.example)")
        lines.extend(f"{key}={user[key]}" for key in leftovers)
    return "\n".join(lines).rstrip("\n") + "\n"


def migrate_env_file(root: Path, new_version: str | None, log: Log = print) -> None:
    """Rewrite ``root/.env`` against ``root/.env.example``."""

    env_path = root / ".env"
    template_path = root / ".env.example"
    if not template_path.is_file():
        log("No .env.example in the new version; leaving .env as it is.")
        return
    template = template_path.read_text(encoding="utf-8")
    old = env_path.read_text(encoding="utf-8") if env_path.is_file() else ""
    migrated = migrate_env(old, template, new_version)
    if migrated != old:
        env_path.write_text(migrated, encoding="utf-8")
        added = sorted(set(parse_env(template)) - set(parse_env(old)))
        if added:
            log(f"Added new settings to .env: {', '.join(added)}")
    log("Settings migrated (.env).")


# --------------------------------------------------------------------------- #
# File install
# --------------------------------------------------------------------------- #


def _is_preserved(relative: Path) -> bool:
    if relative.parts and relative.parts[0] in PRESERVED_NAMES:
        return True
    return relative.name in PRESERVED_NAMES or relative.name.endswith(PRESERVED_SUFFIXES)


def _release_files(root: Path) -> list[Path]:
    """Every file under ``root`` that belongs to the release, as relative paths."""

    files = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and not _is_preserved(relative):
            files.append(relative)
    return files


def download_release(url: str, destination: Path, timeout: float = 60.0) -> Path:
    """Download the release zip into ``destination`` and return its path."""

    if not url.startswith("https://"):
        raise UpdateError(f"Refusing to download from a non-HTTPS URL: {url}")
    archive = destination / "release.zip"
    request = urllib.request.Request(url, headers={"User-Agent": "MissionchiefBot-X-auto-update"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, archive.open("wb") as out:  # nosec B310
            shutil.copyfileobj(response, out)
    except Exception as error:
        raise UpdateError(f"Download failed: {error}") from error
    return archive


def extract_release(archive: Path, destination: Path) -> Path:
    """Unpack the zip safely and return the folder holding the project files."""

    target = destination / "extracted"
    target.mkdir()
    try:
        with zipfile.ZipFile(archive) as bundle:
            base = target.resolve()
            for member in bundle.namelist():
                resolved = (target / member).resolve()
                if resolved != base and base not in resolved.parents:
                    raise UpdateError(f"Unsafe path in update archive: {member}")
            bundle.extractall(target)  # nosec B202 - every member checked above
    except zipfile.BadZipFile as error:
        raise UpdateError(f"The downloaded update is not a valid zip: {error}") from error

    # GitHub zipballs wrap everything in one "<owner>-<repo>-<sha>/" folder.
    entries = [entry for entry in target.iterdir() if entry.name != "__MACOSX"]
    source = entries[0] if len(entries) == 1 and entries[0].is_dir() else target
    if not (source / "Main.py").is_file():
        raise UpdateError("The downloaded update doesn't look like MissionchiefBot-X (Main.py missing).")
    return source


def backup_install(root: Path, label: str) -> Path:
    """Copy the release files of the current install into the backup folder."""

    safe_label = re.sub(r"[^A-Za-z0-9._-]", "_", label) or "previous"
    backup = root / BACKUP_DIR_NAME / safe_label
    if backup.exists():
        shutil.rmtree(backup)
    for relative in _release_files(root):
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, destination)
    env = root / ".env"
    if env.is_file():
        shutil.copy2(env, backup / ".env")
    return backup


def restore_backup(root: Path, backup: Path) -> None:
    """Put a backup made by :func:`backup_install` back in place."""

    for relative in _release_files(root):
        if not (backup / relative).exists():
            (root / relative).unlink(missing_ok=True)
    for path in backup.rglob("*"):
        if path.is_file():
            destination = root / path.relative_to(backup)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)


def install_files(source: Path, root: Path) -> None:
    """Copy the new release over the install and drop files it removed."""

    new_files = set(_release_files(source))
    for relative in _release_files(root):
        if relative not in new_files:
            (root / relative).unlink(missing_ok=True)
    for relative in new_files:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)


def install_dependencies(root: Path, log: Log = print) -> None:
    """Update Python packages and the Playwright browser for the new version."""

    python = sys.executable
    requirements = root / "requirements.txt"
    commands = []
    if requirements.is_file():
        commands.append([python, "-m", "pip", "install", "--upgrade", "-r", str(requirements)])
    commands.append([python, "-m", "playwright", "install", "chromium"])
    for command in commands:
        log(f"> {' '.join(command[1:])}")
        result = subprocess.run(command, cwd=root, check=False)  # nosec B603
        if result.returncode:
            raise UpdateError(
                f"'{' '.join(command[1:])}' failed (exit {result.returncode}). "
                "The new files are installed; run setup_environment.py to finish."
            )


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def perform_update(
    release: dict,
    installed: str,
    root: Path = PROJECT_ROOT,
    log: Log = print,
    install_deps: bool = True,
) -> None:
    """Install ``release`` over ``root``. Raises :class:`UpdateError` on failure."""

    blocked = can_self_update(root)
    if blocked:
        raise UpdateError(blocked)
    url = release.get("zipball_url")
    if not url:
        raise UpdateError("The release has no download link.")
    new_version = str(release.get("tag_name") or "").lstrip("v") or None

    with tempfile.TemporaryDirectory(prefix="mcb-update-") as temp:
        log(f"Downloading {release.get('tag_name')}...")
        source = extract_release(download_release(str(url), Path(temp)), Path(temp))

        log("Backing up the current version...")
        backup = backup_install(root, installed)
        try:
            log("Installing new files...")
            install_files(source, root)
            migrate_env_file(root, new_version, log)
        except Exception as error:
            log("Update failed, restoring the previous version...")
            restore_backup(root, backup)
            raise UpdateError(f"Could not install the update: {error}") from error
    log(f"Previous version saved to {backup}")

    if install_deps:
        log("Updating dependencies...")
        install_dependencies(root, log)
    log(f"Updated to {new_version}.")


def restart() -> int:
    """Start the updated bot in a fresh process and return its exit code."""

    return subprocess.call([sys.executable, *sys.argv])  # nosec B603
