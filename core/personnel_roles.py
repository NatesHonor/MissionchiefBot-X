"""Region-aware personnel requirements.

Mission pages list personnel under localized labels ("Minimum firefighters",
"Mindestens Feuerwehrleute"). This module turns such a label into a role, finds
the vehicle classes that carry that role, and works out how many people each of
the player's vehicles really carries, so the dispatcher can send exactly enough
vehicles: 3 firefighters with 3 per truck is one truck, with 2 per truck it is
two trucks.

Vehicle classes ("firetruck", "patrol car") are resolved through each region's
existing vehicle aliases and options, so one shared table works in every region.
"""

from __future__ import annotations

import importlib
import re
import unicodedata

from utils.personnel_options import get_personnel_options

from .vehicle_mapping import normalize_vehicle_name

# Gathered document: vehicle id -> people currently assigned to that vehicle.
CREW_DOCUMENT = "vehicle_crew.json"

# Role words used on MissionChief mission pages across languages. A label names
# a role when it contains one of these as a whole word, so prefixes such as
# "minimum" or "mindestens" do not matter.
ROLE_TERMS: dict[str, tuple[str, ...]] = {
    "firefighter": (
        "firefighter",
        "firefighters",
        "fire fighter",
        "fire fighters",
        "feuerwehrleute",
        "feuerwehrmann",
        "feuerwehrmänner",
        "brandweerlieden",
        "brandweermensen",
        "brandweerlui",
        "strażak",
        "strażacy",
        "strażaków",
        "bombeiro",
        "bombeiros",
        "pompier",
        "pompiers",
        "sapeur-pompier",
        "sapeurs-pompiers",
        "brandman",
        "brandmän",
        "brandmand",
        "brandmænd",
    ),
    "police officer": (
        "policeman",
        "policemen",
        "police officer",
        "police officers",
        "polizist",
        "polizisten",
        "polizeibeamte",
        "polizeibeamter",
        "politieagent",
        "politieagenten",
        "policjant",
        "policjanci",
        "policjantów",
        "policial",
        "policiais",
        "policier",
        "policiers",
        "poliser",
        "politibetjent",
        "politibetjente",
    ),
}


def _fold(value) -> str:
    text = unicodedata.normalize("NFC", str(value or "")).casefold()
    text = re.sub(r"\([^)]*\)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_personnel_role(name) -> str | None:
    """Return the canonical role named by a localized label, if any."""

    text = _fold(name)
    if not text:
        return None
    for role, terms in ROLE_TERMS.items():
        for term in terms:
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text):
                return role
    return None


def _region_personnel_options(profile, key) -> dict:
    """Optional per-region override: ``PERSONNEL_OPTIONS`` in the region module."""

    try:
        module = importlib.import_module(profile.vehicle_options_module)
    except Exception:
        return {}
    table = getattr(module, "PERSONNEL_OPTIONS", None)
    if not isinstance(table, dict):
        return {}
    wanted = normalize_vehicle_name(key)
    for candidate, options in table.items():
        if normalize_vehicle_name(candidate) == wanted and isinstance(options, dict):
            return dict(options)
    return {}


def personnel_vehicle_options(name, profile, extra_keys=()) -> tuple[str, dict[str, int]]:
    """Return ``(role, {vehicle class: fallback crew per vehicle})`` for a label.

    The fallback crew is only used when the game did not report how many people
    a vehicle actually carries.
    """

    stripped = re.sub(r"\([^)]*\)", "", str(name or "")).strip()
    keys = [*extra_keys, name, normalize_vehicle_name(name), stripped, normalize_vehicle_name(stripped)]
    role = detect_personnel_role(name)
    if role:
        keys.append(role)
    for key in keys:
        if not key:
            continue
        key = str(key).strip()
        options = _region_personnel_options(profile, key) or get_personnel_options(key)
        if options:
            return key, options
    return str(name or ""), {}


def vehicle_crew(profile) -> dict[str, int]:
    """Load the gathered crew sizes for this region's vehicles."""

    value = profile.load_json(CREW_DOCUMENT, {})
    if not isinstance(value, dict):
        return {}
    crew = {}
    for vehicle_id, count in value.items():
        try:
            crew[str(vehicle_id)] = max(0, int(count))
        except (TypeError, ValueError):
            continue
    return crew


def crew_from_records(records) -> dict[str, int]:
    """Read each vehicle's assigned personnel from vehicle API records."""

    crew = {}
    for record in records or []:
        if not isinstance(record, dict):
            continue
        vehicle_id = record.get("id")
        count = record.get("assigned_personnel_count")
        if vehicle_id is None or count is None:
            continue
        try:
            crew[str(vehicle_id)] = max(0, int(count))
        except (TypeError, ValueError):
            continue
    return crew


def _crew_size(value, fallback) -> int:
    for candidate in (value, fallback):
        if candidate is None:
            continue
        try:
            return max(0, int(candidate))
        except (TypeError, ValueError):
            continue
    return 0


def crew_groups(candidates, crew, locked_ids=(), mission_locked_ids=()):
    """Group free candidate vehicles by class and real crew size.

    ``candidates`` maps a vehicle class to ``(fallback_crew, vehicle_ids)``.
    Returns ``(groups, covered)``: ``groups`` maps ``(class, crew)`` to the free
    vehicle ids with that crew, and ``covered`` is the number of people already
    on vehicles this mission has selected, so they are not sent twice.
    """

    locked = {str(vehicle_id) for vehicle_id in locked_ids}
    mission_locked = {str(vehicle_id) for vehicle_id in mission_locked_ids}
    groups: dict[tuple[str, int], list[str]] = {}
    covered = 0
    seen: set[str] = set()
    for vehicle_class, (fallback, ids) in candidates.items():
        for vehicle_id in ids:
            vehicle_id = str(vehicle_id)
            if vehicle_id in seen:
                continue
            seen.add(vehicle_id)
            capacity = _crew_size(crew.get(vehicle_id), fallback)
            if vehicle_id in mission_locked:
                covered += capacity
                continue
            if vehicle_id in locked or capacity <= 0:
                continue
            groups.setdefault((vehicle_class, capacity), []).append(vehicle_id)
    return groups, covered
