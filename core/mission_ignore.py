"""Configuration and matching helpers for missions users do not want scanned."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .vehicle_mapping import normalize_vehicle_name


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (bytes, Mapping)):
        return [str(item) for item in value if str(item or "").strip()]
    return []


@dataclass(frozen=True)
class MissionIgnoreRules:
    """Normalized mission IDs, names, and name fragments to skip."""

    mission_ids: frozenset[str] = frozenset()
    mission_names: frozenset[str] = frozenset()
    name_fragments: tuple[str, ...] = ()

    def matches(self, mission_id, *names: str | None) -> bool:
        if str(mission_id or "") in self.mission_ids:
            return True
        normalized_names = {
            normalize_vehicle_name(name)
            for name in names
            if normalize_vehicle_name(name)
        }
        if normalized_names & self.mission_names:
            return True
        return any(
            fragment in name
            for name in normalized_names
            for fragment in self.name_fragments
        )


def load_mission_ignore_rules(profile) -> MissionIgnoreRules:
    """Load one region's optional ``mission_ignore_list.json`` safely.

    A simple JSON array is accepted for convenience.  Numeric entries are
    active mission IDs; other entries are exact mission names.  The object
    form adds explicit ``mission_ids``, ``mission_names``, and ``contains``
    lists for stable matching across mission ID changes.
    """

    raw = profile.load_json("mission_ignore_list.json", {})
    if isinstance(raw, list):
        ids = [value for value in raw if str(value).strip().isdigit()]
        names = [value for value in raw if not str(value).strip().isdigit()]
        fragments = []
    elif isinstance(raw, Mapping):
        ids = _strings(raw.get("mission_ids", raw.get("ids", [])))
        names = _strings(raw.get("mission_names", raw.get("names", [])))
        fragments = _strings(raw.get("contains", raw.get("name_fragments", [])))
    else:
        ids, names, fragments = [], [], []

    return MissionIgnoreRules(
        mission_ids=frozenset(str(value).strip() for value in ids if str(value).strip()),
        mission_names=frozenset(
            normalize_vehicle_name(value) for value in names if normalize_vehicle_name(value)
        ),
        name_fragments=tuple(
            normalize_vehicle_name(value)
            for value in fragments
            if normalize_vehicle_name(value)
        ),
    )


def _index_name_map(mission_index) -> dict[str, str]:
    if isinstance(mission_index, Mapping):
        mission_index = list(mission_index.values())
    if not isinstance(mission_index, list):
        return {}
    result = {}
    for record in mission_index:
        if not isinstance(record, Mapping):
            continue
        name = str(record.get("name") or record.get("mission_name") or "").strip()
        if not name:
            continue
        for key in ("id", "mission_id", "base_mission_id", "mission_type_id"):
            value = record.get(key)
            if value is not None:
                result[str(value)] = name
    return result


def filter_ignored_mission_ids(
    mission_ids,
    rules: MissionIgnoreRules,
    mission_index=None,
    marker_records: Mapping[str, Mapping] | None = None,
    cached_missions: Mapping[str, Mapping] | None = None,
) -> tuple[list[str], list[tuple[str, str]]]:
    """Remove ignored active IDs before mission detail pages are collected."""

    index_names = _index_name_map(mission_index)
    marker_records = marker_records or {}
    cached_missions = cached_missions or {}
    kept = []
    ignored = []
    for value in mission_ids:
        mission_id = str(value)
        marker = marker_records.get(mission_id, {})
        cached = cached_missions.get(mission_id, {})
        type_id = marker.get("type_id")
        names = (
            marker.get("name"),
            index_names.get(str(type_id)) if type_id is not None else None,
            cached.get("mission_name"),
        )
        if rules.matches(mission_id, *names):
            reason = next(
                (
                    str(name)
                    for name in names
                    if name and rules.matches("", name)
                ),
                "configured rule",
            )
            ignored.append((mission_id, reason))
        else:
            kept.append(mission_id)
    return kept, ignored
