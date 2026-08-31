"""Per-region vehicle inventory and mission locks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from utils.pretty_print import display_info


@dataclass
class VehicleState:
    data_file: Path
    _data: dict | None = None
    _locked: dict[str, str] = field(default_factory=dict)

    def get_data(self) -> dict:
        if self._data is None:
            if not self.data_file.exists():
                self._data = {}
            else:
                with self.data_file.open("r", encoding="utf-8") as stream:
                    self._data = json.load(stream)
        return self._data

    def refresh(self) -> dict:
        self._data = None
        return self.get_data()

    def clear_locks(self) -> None:
        self._locked.clear()

    def lock(self, vehicle_id: str, mission_id: str) -> bool:
        if vehicle_id in self._locked:
            return False
        self._locked[vehicle_id] = mission_id
        return True

    def is_locked(self, vehicle_id: str) -> bool:
        return vehicle_id in self._locked

    def unlock(self, vehicle_id: str, mission_id: str | None = None) -> None:
        if mission_id is None or self._locked.get(vehicle_id) == mission_id:
            self._locked.pop(vehicle_id, None)

    def free_for_mission(self, mission_id: str) -> None:
        self._locked = {
            vehicle_id: locked_mission
            for vehicle_id, locked_mission in self._locked.items()
            if locked_mission != mission_id
        }
        display_info(f"Freed up vehicles for {mission_id}")

    def locked(self, mission_id: str | None = None) -> dict[str, str]:
        if mission_id is None:
            return dict(self._locked)
        return {
            vehicle_id: locked_mission
            for vehicle_id, locked_mission in self._locked.items()
            if locked_mission == mission_id
        }


_states: dict[Path, VehicleState] = {}


def get_vehicle_state(profile) -> VehicleState:
    key = profile.vehicle_file.resolve()
    if key not in _states:
        _states[key] = VehicleState(key)
    return _states[key]
