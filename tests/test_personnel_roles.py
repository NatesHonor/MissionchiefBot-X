import asyncio

import pytest

from core.dispatching import personnel as personnel_module
from core.dispatching.personnel import handle_personnel, plan_personnel_vehicles
from core.personnel_roles import (
    crew_from_records,
    crew_groups,
    detect_personnel_role,
    personnel_vehicle_options,
)
from core.regions import get_region_profile


@pytest.mark.parametrize(
    ("label", "role"),
    [
        ("Minimum firefighters", "firefighter"),
        ("minimum feuerwehrleute", "firefighter"),
        ("Mindestens Feuerwehrleute", "firefighter"),
        ("Mindestens Polizisten", "police officer"),
        ("Minimum policemen", "police officer"),
        ("Minimaal brandweerlieden", "firefighter"),
        ("Minimalna liczba strażaków", "firefighter"),
        ("Löschfahrzeuge", None),
        ("Fire trucks", None),
    ],
)
def test_detects_role_in_any_language(label, role):
    assert detect_personnel_role(label) == role


def test_firefighter_label_maps_to_firetrucks_in_every_region():
    for key in ("us", "ger"):
        role, options = personnel_vehicle_options("Mindestens Feuerwehrleute", get_region_profile(key))
        assert role == "firefighter"
        assert "firetruck" in options


def test_crew_from_records_reads_assigned_personnel():
    records = [
        {"id": 1, "assigned_personnel_count": 3},
        {"id": 2, "assigned_personnel_count": "2"},
        {"id": 3},
        {"id": 4, "assigned_personnel_count": "x"},
    ]
    assert crew_from_records(records) == {"1": 3, "2": 2}


def _plan(needed, crew, ids, fallback=3):
    groups, covered = crew_groups({"firetruck": (fallback, ids)}, crew)
    plan = plan_personnel_vehicles(
        needed - covered,
        [(group, group[1], len(vehicle_ids)) for group, vehicle_ids in groups.items()],
    )
    return sum(quantity for _group, quantity in plan)


def test_three_firefighters_with_three_per_truck_sends_one_truck():
    assert _plan(3, {"1": 3, "2": 3}, ["1", "2"]) == 1


def test_three_firefighters_with_two_per_truck_sends_two_trucks():
    assert _plan(3, {"1": 2, "2": 2, "3": 2}, ["1", "2", "3"]) == 2


def test_prefers_fewest_vehicles_with_mixed_crews():
    assert _plan(6, {"1": 2, "2": 2, "3": 6}, ["1", "2", "3"]) == 1


def test_uses_fallback_crew_when_unknown():
    assert _plan(3, {}, ["1", "2"], fallback=3) == 1


def test_skips_empty_and_locked_vehicles():
    groups, covered = crew_groups({"firetruck": (3, ["1", "2", "3"])}, {"1": 0}, locked_ids=["2"])
    assert covered == 0
    assert groups == {("firetruck", 3): ["3"]}


def test_counts_people_already_selected_for_this_mission():
    groups, covered = crew_groups(
        {"firetruck": (3, ["1", "2"])},
        {"1": 2, "2": 3},
        mission_locked_ids=["1"],
    )
    assert covered == 2
    assert groups == {("firetruck", 3): ["2"]}


def test_german_firefighter_requirement_dispatches_by_crew(monkeypatch):
    profile = get_region_profile("ger")
    selected = []

    async def fake_find(vehicle_type, *_args, **_kwargs):
        return ["10", "11", "12"] if vehicle_type == "firetruck" else []

    async def fake_select(_page, ids, count, *_args, **_kwargs):
        selected.extend(ids[:count])
        return min(count, len(ids))

    monkeypatch.setattr(personnel_module, "find_vehicle_ids", fake_find)
    monkeypatch.setattr(personnel_module, "select_vehicles", fake_select)
    monkeypatch.setattr(personnel_module, "vehicle_crew", lambda _profile: {"10": 2, "11": 2, "12": 2})

    class Settings:
        dispatch_incomplete = False

    data = {"vehicles": [], "personnel": [{"name": "Mindestens Feuerwehrleute", "count": 3}]}
    missing = []
    asyncio.run(handle_personnel(None, data, missing, 1, profile=profile, settings=Settings()))

    assert len(selected) == 2
    assert missing == []
