"""Build the shipped region-defaults seed database.

Reads the region default JSON (vehicle aliases, personnel aliases,
requirement mappings, mission ignore lists) and writes them into
``assets/region_defaults.sqlite3``. This seed only ever contains shipped
defaults; it never contains gathered player data and is never the user's
database.

Usage:
    python tools/build_seed_db.py [source_dir]

``source_dir`` defaults to ``regions/defaults``. Pass a git-exported copy to
rebuild the seed after the JSON folders have been removed.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "assets" / "region_defaults.sqlite3"
DOCUMENTS = (
    "vehicle_aliases.json",
    "personnel_aliases.json",
    "requirement_mapping.json",
    "mission_ignore_list.json",
)


def version_of(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def build(source: Path, destination: Path = SEED_PATH) -> int:
    regions = sorted(path.name for path in source.iterdir() if path.is_dir())
    if not regions:
        raise SystemExit(f"No region folders found in {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    try:
        connection.execute(
            """
            CREATE TABLE defaults (
                region   TEXT NOT NULL,
                document TEXT NOT NULL,
                content  TEXT NOT NULL,
                version  TEXT NOT NULL,
                PRIMARY KEY (region, document)
            )
            """
        )
        count = 0
        for region in regions:
            for document in DOCUMENTS:
                path = source / region / document
                if not path.is_file():
                    raise SystemExit(f"Missing default: {path}")
                value = json.loads(path.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO defaults VALUES (?, ?, ?, ?)",
                    (region, document, json.dumps(value, ensure_ascii=False, separators=(",", ":")), version_of(value)),
                )
                count += 1
        connection.commit()
        connection.execute("VACUUM")
    finally:
        connection.close()
    temporary.replace(destination)
    return count


def verify(source: Path, destination: Path = SEED_PATH) -> None:
    connection = sqlite3.connect(f"file:{destination}?mode=ro", uri=True)
    try:
        rows = {
            (region, document): json.loads(content)
            for region, document, content in connection.execute("SELECT region, document, content FROM defaults")
        }
    finally:
        connection.close()
    for region_dir in sorted(path for path in source.iterdir() if path.is_dir()):
        for document in DOCUMENTS:
            expected = json.loads((region_dir / document).read_text(encoding="utf-8"))
            actual = rows.pop((region_dir.name, document), None)
            if actual != expected:
                raise SystemExit(f"Seed mismatch for {region_dir.name}/{document}")
    if rows:
        raise SystemExit(f"Unexpected seed rows: {sorted(rows)}")


if __name__ == "__main__":
    source_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "regions" / "defaults"
    written = build(source_dir)
    verify(source_dir)
    print(f"Wrote and verified {written} defaults in {SEED_PATH.relative_to(ROOT)}")
