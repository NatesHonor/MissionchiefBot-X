"""SQLite-backed storage for the bot's JSON data documents.

Every data document (region aliases, requirement maps, vehicle/building
caches, mission data, tasks, ...) is stored as one row in a single SQLite
database. JSON is only used for the small shipped region defaults and
human-readable import/export. Callers keep passing the same file
paths they always used; each path is turned into a stable document key such as
``regions/us/data/vehicle_data.json``.

Compatibility rules, so nothing breaks during the transition:

* Legacy JSON files are imported automatically the first time they are read.
* Documents imported from a bundled JSON file are re-imported when that file
  changes (for example after pulling an update with new region data).
* Documents written by the bot itself always win over any JSON file on disk.
* If the database cannot be opened, reads fall back to the JSON file directly.

The database lives at ``data/missionchief.sqlite3`` by default. Set
``MISSIONCHIEF_DB_PATH`` to use a different location.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "missionchief.sqlite3"

SOURCE_FILE = "file"
SOURCE_APP = "app"
# Shipped defaults (aliases, mappings, ignore lists). They are written to the
# database on startup and kept there. A default never overwrites a document the
# bot or the user changed (SOURCE_APP); it is refreshed only when the shipped
# default itself changes. Gathered data (vehicles, buildings, missions) is never
# a default: when it is missing the bot gathers it from the game.
SOURCE_DEFAULT = "default"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    key          TEXT PRIMARY KEY,
    content      TEXT NOT NULL,
    source       TEXT NOT NULL DEFAULT 'app',
    source_mtime REAL,
    updated_at   REAL NOT NULL
);
"""

_lock = threading.RLock()


def database_path() -> Path:
    """Return the configured database location."""

    override = os.getenv("MISSIONCHIEF_DB_PATH", "").strip()
    path = Path(override).expanduser() if override else DEFAULT_DB_PATH
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


@contextmanager
def connect(path: str | os.PathLike[str] | None = None) -> Iterator[sqlite3.Connection]:
    """Open the database, create the schema if needed, and commit on success."""

    db_path = Path(path) if path else database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=30)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA temp_store=MEMORY")
        connection.execute("PRAGMA cache_size=-2048")  # 2 MiB page cache, not the SQLite default.
        connection.executescript(_SCHEMA)
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def document_key(path: str | os.PathLike[str]) -> str:
    """Turn a data file path into a stable, project-relative document key."""

    supplied = Path(path).expanduser()
    resolved = supplied if supplied.is_absolute() else PROJECT_ROOT / supplied
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def key_path(key: str) -> Path:
    """Return the legacy JSON file path that corresponds to a document key."""

    path = Path(key)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _file_mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _read_json_file(path: Path) -> tuple[bool, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return True, json.load(stream)
    except (FileNotFoundError, OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False, None


def _write_row(connection: sqlite3.Connection, key: str, value: Any, source: str, source_mtime: float | None) -> None:
    connection.execute(
        """
        INSERT INTO documents (key, content, source, source_mtime, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            content = excluded.content,
            source = excluded.source,
            source_mtime = excluded.source_mtime,
            updated_at = excluded.updated_at
        """,
        (key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), source, source_mtime, time.time()),
    )


def load_document(path: str | os.PathLike[str], default: Any = None) -> Any:
    """Load one data document, importing the legacy JSON file when needed."""

    file_path = Path(path)
    key = document_key(file_path)
    mtime = _file_mtime(file_path)
    try:
        with _lock, connect() as connection:
            row = connection.execute(
                "SELECT content, source, source_mtime FROM documents WHERE key = ?",
                (key,),
            ).fetchone()
            stale_import = (
                row is not None
                and row[1] == SOURCE_FILE
                and mtime is not None
                and row[2] != mtime
            )
            if row is not None and not stale_import:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return default
            found, value = _read_json_file(file_path)
            if not found:
                if row is not None:
                    try:
                        return json.loads(row[0])
                    except json.JSONDecodeError:
                        return default
                return default
            _write_row(connection, key, value, SOURCE_FILE, mtime)
            return value
    except sqlite3.Error:
        found, value = _read_json_file(file_path)
        return value if found else default


def save_document(path: str | os.PathLike[str], value: Any) -> str:
    """Store one data document written by the bot and return its key."""

    key = document_key(path)
    with _lock, connect() as connection:
        _write_row(connection, key, value, SOURCE_APP, None)
    return key


def seed_document(path: str | os.PathLike[str], value: Any, version: str) -> bool:
    """Store a shipped default unless the document is already owned by the bot.

    ``version`` identifies the shipped default (for example a content hash).
    Returns True when the database was written.
    """

    key = document_key(path)
    try:
        with _lock, connect() as connection:
            row = connection.execute(
                "SELECT source, source_mtime FROM documents WHERE key = ?",
                (key,),
            ).fetchone()
            if row is not None:
                source, stored_version = row
                if source == SOURCE_APP:
                    return False
                if source == SOURCE_DEFAULT and stored_version == version:
                    return False
            connection.execute(
                """
                INSERT INTO documents (key, content, source, source_mtime, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    content = excluded.content,
                    source = excluded.source,
                    source_mtime = excluded.source_mtime,
                    updated_at = excluded.updated_at
                """,
                (key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), SOURCE_DEFAULT, version, time.time()),
            )
            return True
    except sqlite3.Error:
        return False


def document_has_records(path: str | os.PathLike[str]) -> bool:
    """Return True when a stored document holds at least one record.

    Missing, empty, or corrupt documents count as having no records, so callers
    know the data still needs to be gathered.
    """

    value = load_document(path, None)
    if isinstance(value, (dict, list)):
        return len(value) > 0
    return value is not None


def document_exists(path: str | os.PathLike[str]) -> bool:
    """Return True when a document is stored or its legacy JSON file exists."""

    file_path = Path(path)
    if file_path.is_file():
        return True
    try:
        with _lock, connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM documents WHERE key = ?",
                (document_key(file_path),),
            ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False


def document_updated_at(path: str | os.PathLike[str]) -> float | None:
    """Return when a document was last stored, falling back to the JSON file's mtime."""

    file_path = Path(path)
    try:
        with _lock, connect() as connection:
            row = connection.execute(
                "SELECT source, source_mtime, updated_at FROM documents WHERE key = ?",
                (document_key(file_path),),
            ).fetchone()
    except sqlite3.Error:
        row = None
    if row is None:
        return _file_mtime(file_path)
    source, source_mtime, updated_at = row
    if source == SOURCE_FILE and source_mtime is not None:
        return source_mtime
    return updated_at


def delete_document(key: str) -> bool:
    """Delete a stored document by key. Returns True when a row was removed."""

    with _lock, connect() as connection:
        cursor = connection.execute("DELETE FROM documents WHERE key = ?", (key,))
        return cursor.rowcount > 0


def list_documents(prefix: str = "") -> list[dict[str, Any]]:
    """List stored documents with size, source, and last update time."""

    with _lock, connect() as connection:
        rows = connection.execute(
            """
            SELECT key, source, LENGTH(content), updated_at
            FROM documents
            WHERE key LIKE ? ESCAPE '\\'
            ORDER BY key
            """,
            (prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%",),
        ).fetchall()
    return [
        {"key": key, "source": source, "size": size, "updated_at": updated_at}
        for key, source, size, updated_at in rows
    ]


def get_document(key: str, default: Any = None) -> Any:
    """Load a document by its key (used by the data management tool)."""

    return load_document(key_path(key), default)


def set_document(key: str, value: Any) -> None:
    """Store a document by its key (used by the data management tool)."""

    save_document(key_path(key), value)


def import_json_files(root: str | os.PathLike[str] | None = None) -> list[str]:
    """Import every JSON data file under the project into the database."""

    base = Path(root) if root else PROJECT_ROOT
    imported: list[str] = []
    skipped_parts = {".git", ".venv", "venv", "node_modules", "__pycache__", ".idea", "logs", ".github"}
    with _lock, connect() as connection:
        for file_path in sorted(base.rglob("*.json")):
            folders = file_path.relative_to(base).parts[:-1]
            if skipped_parts.intersection(folders):
                continue
            # The top-level data/ folder holds the database and exports, not source data.
            if folders and folders[0] == "data":
                continue
            # Tooling config such as release-please manifests is not bot data.
            if not folders:
                continue
            # Shipped region defaults are seeded by core.region_defaults under
            # their regions/<region>/data/ keys, not imported as files.
            if "defaults" in folders:
                continue
            found, value = _read_json_file(file_path)
            if not found:
                continue
            key = document_key(file_path)
            existing = connection.execute("SELECT source FROM documents WHERE key = ?", (key,)).fetchone()
            if existing is not None and existing[0] == SOURCE_APP:
                continue
            _write_row(connection, key, value, SOURCE_FILE, _file_mtime(file_path))
            imported.append(key)
    return imported
