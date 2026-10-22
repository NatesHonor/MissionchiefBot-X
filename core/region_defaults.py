"""Shipped region defaults and gathered-data rules for the SQLite store.

Every region document lives in the user's SQLite database (see
:mod:`core.data_store`). There are two kinds:

* **Defaults** ship with the bot inside one read-only seed database,
  ``assets/region_defaults.sqlite3``: vehicle aliases, personnel aliases,
  requirement mappings and the mission ignore list. On startup they are copied
  *row by row* into the user's database, where they persist. The seed file is
  never copied over the user's database, and a default never overwrites a
  document the bot or the user changed; it is only refreshed when the shipped
  default itself changes.
* **Gathered** documents come from the game for one player: vehicle IDs,
  building IDs, the active-mission snapshot and the mission index. They are
  never shipped. When one is missing or empty in the database, the bot gathers
  it from the game and stores it.

Rebuild the seed with ``python tools/build_seed_db.py <defaults-json-dir>``.
Document keys keep their historic ``regions/<region>/data/<file>.json`` form so
existing user databases keep working.
"""

from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from .data_store import seed_document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED_DATABASE = PROJECT_ROOT / "assets" / "region_defaults.sqlite3"

# Shipped with the bot and kept in the database.
DEFAULT_DOCUMENTS: tuple[str, ...] = (
    "vehicle_aliases.json",
    "personnel_aliases.json",
    "requirement_mapping.json",
    "mission_ignore_list.json",
)

# Gathered from the game for this player. Never shipped or seeded.
GATHERED_DOCUMENTS: tuple[str, ...] = (
    "vehicle_data.json",
    "building_data.json",
    "mission_data.json",
    "mission_index.json",
)

# Used when the seed has no row for a default document.
_FALLBACKS: dict[str, Any] = {
    "vehicle_aliases.json": {},
    "personnel_aliases.json": {},
    "requirement_mapping.json": {},
    "mission_ignore_list.json": {"mission_ids": [], "mission_names": [], "contains": []},
}


@lru_cache(maxsize=1)
def _seed_rows() -> dict[tuple[str, str], tuple[Any, str]]:
    """Read the whole seed once (it is small) through a read-only connection."""

    try:
        connection = sqlite3.connect(f"file:{SEED_DATABASE.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return {}
    try:
        return {
            (region, document): (json.loads(content), version)
            for region, document, content, version in connection.execute(
                "SELECT region, document, content, version FROM defaults"
            )
        }
    except (sqlite3.Error, json.JSONDecodeError):
        return {}
    finally:
        connection.close()


def shipped_default(region_key: str, filename: str) -> Any:
    """Return one shipped default from the seed database."""

    row = _seed_rows().get((region_key, filename))
    return row[0] if row else _FALLBACKS[filename]


def has_shipped_default(region_key: str, filename: str) -> bool:
    return (region_key, filename) in _seed_rows()


def seed_region_defaults(region_key: str, data_dir: Path) -> list[str]:
    """Copy one region's shipped defaults into the user's database.

    Only individual default rows are written, never the seed file itself, and
    user-edited documents are left untouched. ``data_dir`` is the region's
    document-key folder. Returns the filenames that were written.
    """

    written: list[str] = []
    for filename in DEFAULT_DOCUMENTS:
        row = _seed_rows().get((region_key, filename))
        if row is None:
            continue
        value, version = row
        if seed_document(data_dir / filename, value, version):
            written.append(filename)
    return written
