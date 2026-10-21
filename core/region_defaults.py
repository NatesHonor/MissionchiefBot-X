"""Shipped region defaults and gathered-data rules for the SQLite store.

Every region document lives in SQLite (see :mod:`core.data_store`). There are
two kinds:

* **Defaults** ship with the bot in ``regions/defaults/<region>/*.json``:
  vehicle aliases, personnel aliases, requirement mappings and the mission
  ignore list. On startup they are seeded into the database and they persist
  there. A default never overwrites a document the bot or the user changed; it
  is only refreshed when the shipped default itself changes.
* **Gathered** documents come from the game for one player: vehicle IDs,
  building IDs, the active-mission snapshot and the mission index. They are
  never shipped. When one is missing or empty in the database, the bot gathers
  it from the game and stores it.

Each region is a single module (``regions/<region>.py``) holding its vehicle
option table; there are no per-region folders. Document keys keep their
historic ``regions/<region>/data/<file>.json`` form so existing databases keep
working.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .data_store import seed_document

PROJECT_ROOT = Path(__file__).resolve().parents[1]

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

# Used when a region has no shipped file for a default document.
_FALLBACKS: dict[str, Any] = {
    "vehicle_aliases.json": {},
    "personnel_aliases.json": {},
    "requirement_mapping.json": {},
    "mission_ignore_list.json": {"mission_ids": [], "mission_names": [], "contains": []},
}


def defaults_dir(region_key: str) -> Path:
    return PROJECT_ROOT / "regions" / "defaults" / region_key


def shipped_default(region_key: str, filename: str) -> Any:
    """Read one shipped default straight from ``regions/defaults/<region>``."""

    path = defaults_dir(region_key) / filename
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (FileNotFoundError, OSError, json.JSONDecodeError, UnicodeDecodeError):
        return _FALLBACKS[filename]


def _version(value: Any) -> str:
    # Prefixed so SQLite never stores it as a number.
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def seed_region_defaults(region_key: str, data_dir: Path) -> list[str]:
    """Seed one region's shipped defaults into the database.

    ``data_dir`` is the region's document-key folder. Returns the filenames that
    were written.
    """

    written: list[str] = []
    for filename in DEFAULT_DOCUMENTS:
        value = shipped_default(region_key, filename)
        if seed_document(data_dir / filename, value, _version(value)):
            written.append(filename)
    return written
