"""Manage MissionchiefBot X data stored in SQLite.

Run with no arguments for an interactive menu:

    python manage_data.py

Or use a command directly:

    python manage_data.py list [prefix]       List stored documents
    python manage_data.py show <key>          Print one document as JSON
    python manage_data.py edit <key> <file>   Replace a document with a JSON file
    python manage_data.py delete <key>        Delete one document
    python manage_data.py import              Import every JSON data file in the project
    python manage_data.py export <folder>     Export every document to JSON files
    python manage_data.py backup [file]       Copy the database to a backup file
    python manage_data.py info                Show database location and totals

Keys are project-relative paths such as ``regions/us/data/vehicle_data.json``.
The database lives at ``data/missionchief.sqlite3`` unless MISSIONCHIEF_DB_PATH
points somewhere else.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from core import data_store


def _format_time(value: float | None) -> str:
    if not value:
        return "-"
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def _format_size(size: int | None) -> str:
    size = size or 0
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def cmd_list(prefix: str = "") -> int:
    documents = data_store.list_documents(prefix)
    if not documents:
        print("No documents stored yet. Run 'import' to load the existing JSON files.")
        return 0
    width = max(len(item["key"]) for item in documents)
    print(f"{'KEY'.ljust(width)}  {'SOURCE':6}  {'SIZE':>9}  UPDATED")
    for item in documents:
        print(
            f"{item['key'].ljust(width)}  {item['source']:6}  "
            f"{_format_size(item['size']):>9}  {_format_time(item['updated_at'])}"
        )
    print(f"\n{len(documents)} document(s).")
    return 0


def cmd_show(key: str) -> int:
    value = data_store.get_document(key, None)
    if value is None:
        print(f"No document found for {key!r}.", file=sys.stderr)
        return 1
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


def cmd_edit(key: str, source: str) -> int:
    try:
        value = json.loads(Path(source).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read valid JSON from {source}: {error}", file=sys.stderr)
        return 1
    data_store.set_document(key, value)
    print(f"Stored {key}.")
    return 0


def cmd_delete(key: str, confirm: bool = True) -> int:
    if confirm:
        answer = input(f"Delete {key}? This cannot be undone. [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled.")
            return 0
    if data_store.delete_document(key):
        print(f"Deleted {key}.")
        return 0
    print(f"No document found for {key!r}.", file=sys.stderr)
    return 1


def cmd_import() -> int:
    imported = data_store.import_json_files()
    print(f"Imported {len(imported)} JSON file(s) into {data_store.database_path()}.")
    return 0


def cmd_export(folder: str) -> int:
    destination = Path(folder)
    documents = data_store.list_documents()
    for item in documents:
        value = data_store.get_document(item["key"], None)
        target = destination / item["key"].lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(documents)} document(s) to {destination.resolve()}.")
    return 0


def cmd_backup(target: str | None = None) -> int:
    source_path = data_store.database_path()
    if not source_path.is_file():
        print(f"No database found at {source_path}.", file=sys.stderr)
        return 1
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = Path(target) if target else source_path.with_name(f"missionchief-backup-{stamp}.sqlite3")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_path) as source, sqlite3.connect(backup_path) as destination:
        source.backup(destination)
    print(f"Backed up database to {backup_path.resolve()}.")
    return 0


def cmd_info() -> int:
    path = data_store.database_path()
    documents = data_store.list_documents() if path.is_file() else []
    total = sum(item["size"] or 0 for item in documents)
    print(f"Database:  {path}")
    print(f"Exists:    {'yes' if path.is_file() else 'no'}")
    print(f"Documents: {len(documents)}")
    print(f"Data size: {_format_size(total)}")
    return 0


def interactive() -> int:
    menu = (
        "\nMissionchiefBot X data manager\n"
        "  1) List documents\n"
        "  2) Show a document\n"
        "  3) Replace a document from a JSON file\n"
        "  4) Delete a document\n"
        "  5) Import existing JSON files\n"
        "  6) Export everything to JSON\n"
        "  7) Back up the database\n"
        "  8) Database info\n"
        "  q) Quit\n"
    )
    while True:
        print(menu)
        choice = input("Choose an option: ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            return 0
        if choice == "1":
            cmd_list(input("Filter by key prefix (blank for all): ").strip())
        elif choice == "2":
            cmd_show(input("Document key: ").strip())
        elif choice == "3":
            cmd_edit(input("Document key: ").strip(), input("Path to JSON file: ").strip())
        elif choice == "4":
            cmd_delete(input("Document key: ").strip())
        elif choice == "5":
            cmd_import()
        elif choice == "6":
            cmd_export(input("Export folder [data/export]: ").strip() or "data/export")
        elif choice == "7":
            cmd_backup(input("Backup file (blank for default): ").strip() or None)
        elif choice == "8":
            cmd_info()
        else:
            print("Unknown option.")


def main(argv: list[str]) -> int:
    if not argv:
        return interactive()
    command, args = argv[0].lower(), argv[1:]
    commands = {
        "list": (cmd_list, 0, 1),
        "show": (cmd_show, 1, 1),
        "edit": (cmd_edit, 2, 2),
        "delete": (cmd_delete, 1, 1),
        "import": (cmd_import, 0, 0),
        "export": (cmd_export, 1, 1),
        "backup": (cmd_backup, 0, 1),
        "info": (cmd_info, 0, 0),
    }
    if command in {"-h", "--help", "help"} or command not in commands:
        print(__doc__)
        return 0 if command in {"-h", "--help", "help"} else 1
    handler, minimum, maximum = commands[command]
    if not minimum <= len(args) <= maximum:
        print(__doc__)
        return 1
    return handler(*args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
