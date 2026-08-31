"""Central region registry and localized data access.

The MissionChief websites share most of their HTML and API contracts, but the
vehicle names, requirement labels, and language-specific text do not.  Every
runtime component receives a :class:`RegionProfile` instead of making its own
region assumptions.
"""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .vehicle_mapping import (
    dedupe_vehicle_terms,
    matching_vehicle_alias_group,
    validate_alias_groups,
    validate_vehicle_aliases,
    normalize_vehicle_name,
)
from utils.personnel_options import get_personnel_options


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RegionProfile:
    key: str
    display_name: str
    base_url: str
    runtime_supported: bool
    data_dir: Path
    vehicle_options_module: str
    language: str = "en"
    notes: str = ""

    @property
    def login_url(self) -> str:
        return f"{self.base_url}users/sign_in"

    @property
    def mission_file(self) -> Path:
        return self.data_dir / "mission_data.json"

    @property
    def mission_index_file(self) -> Path:
        return self.data_dir / "mission_index.json"

    @property
    def mission_ignore_file(self) -> Path:
        return self.data_dir / "mission_ignore_list.json"

    @property
    def vehicle_file(self) -> Path:
        return self.data_dir / "vehicle_data.json"

    @property
    def building_file(self) -> Path:
        return self.data_dir / "building_data.json"

    @property
    def vehicle_aliases_file(self) -> Path:
        return self.data_dir / "vehicle_aliases.json"

    @property
    def personnel_aliases_file(self) -> Path:
        return self.data_dir / "personnel_aliases.json"

    @property
    def requirement_mapping_file(self) -> Path:
        return self.data_dir / "requirement_mapping.json"

    @property
    def entrypoint(self) -> str:
        """Return the standardized compatibility entrypoint for this region."""

        return f"regions.{self.key}.main_{self.key}:main"

    def ensure_data_dir(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir

    def load_json(self, filename: str, default: Any = None) -> Any:
        """Load one region data file without allowing a broken cache to stop startup."""

        try:
            with (self.data_dir / filename).open("r", encoding="utf-8") as stream:
                return json.load(stream)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {} if default is None else default

    def vehicle_aliases(self) -> dict[str, list[str]]:
        value = self.load_json("vehicle_aliases.json", {})
        return value if isinstance(value, dict) else {}

    def personnel_aliases(self) -> dict[str, list[str]]:
        value = self.load_json("personnel_aliases.json", {})
        return value if isinstance(value, dict) else {}

    def requirement_mapping(self) -> dict[str, str]:
        value = self.load_json("requirement_mapping.json", {})
        return value if isinstance(value, dict) else {}

    def validate_data_contract(self) -> list[str]:
        """Return missing profile resources; useful for diagnostics and tests."""

        required = (
            "vehicle_aliases.json",
            "personnel_aliases.json",
            "requirement_mapping.json",
        )
        return [filename for filename in required if not (self.data_dir / filename).is_file()]

    def validate_vehicle_mappings(self) -> list[str]:
        """Validate every regional alias, personnel, and requirement map."""

        errors = [
            f"vehicle_aliases.json: {message}"
            for message in validate_vehicle_aliases(self.vehicle_aliases())
        ]
        personnel_aliases = self.personnel_aliases()
        errors.extend(
            f"personnel_aliases.json: {message}"
            for message in validate_alias_groups(personnel_aliases, "personnel")
        )
        for canonical in personnel_aliases:
            if not get_personnel_options(canonical):
                errors.append(
                    f"personnel_aliases.json: no personnel options resolve for {canonical!r}"
                )

        requirement_mapping = self.requirement_mapping()
        allowed_kinds = {"liquid", "personnel", "tow_vehicle", "pass", "info"}
        normalized_requirement_keys: set[str] = set()
        for key, kind in requirement_mapping.items():
            normalized_key = normalize_vehicle_name(key)
            if not normalized_key:
                errors.append("requirement_mapping.json: empty requirement label")
            elif normalized_key in normalized_requirement_keys:
                errors.append(f"requirement_mapping.json: duplicate label {key!r}")
            normalized_requirement_keys.add(normalized_key)
            if kind not in allowed_kinds:
                errors.append(
                    f"requirement_mapping.json: unsupported kind {kind!r} for {key!r}"
                )

        module = importlib.import_module(self.vehicle_options_module)
        option_map = getattr(module, "VEHICLE_OPTIONS", {})
        if option_map and not isinstance(option_map, dict):
            errors.append("vehicle options must be a mapping")
            return errors

        requests = set(self.vehicle_aliases())
        requests.update(
            synonym
            for synonyms in self.vehicle_aliases().values()
            if isinstance(synonyms, list)
            for synonym in synonyms
        )
        requests.update(option_map)
        for requested in requests:
            if not self.vehicle_options(requested):
                errors.append(f"no options resolve for {requested!r}")
        return errors

    def vehicle_options(self, vehicle_type: str) -> list[str]:
        module = importlib.import_module(self.vehicle_options_module)
        options = list(module.get_vehicle_options(vehicle_type) or [])
        if options:
            return dedupe_vehicle_terms(options)

        aliases = self.vehicle_aliases()
        group = matching_vehicle_alias_group(vehicle_type, aliases)
        if not group:
            return []

        # The option map describes cross-category substitutions (for example,
        # Rescue Engine satisfies a heavy-rescue requirement).  Try every
        # equivalent label in the alias group before falling back to its raw
        # regional names.
        mapped_options: list[str] = []
        for label in group:
            mapped_options.extend(module.get_vehicle_options(label) or [])
        return dedupe_vehicle_terms((*mapped_options, *group))


_REGION_DEFINITIONS = {
    "us": {
        "display_name": "United States",
        "base_url": "https://www.missionchief.com/",
        "vehicle_options_module": "utils.vehicle_options",
        "language": "en",
    },
    "uk": {
        "display_name": "United Kingdom",
        "base_url": "https://www.missionchief.co.uk/",
        "vehicle_options_module": "regions.uk.data.vehicle_options",
        "language": "en",
    },
    "aus": {
        "display_name": "Australia",
        "base_url": "https://www.missionchief-australia.com/",
        "vehicle_options_module": "regions.aus.data.vehicle_options",
        "language": "en",
    },
    "ger": {
        "display_name": "Germany",
        "base_url": "https://www.leitstellenspiel.de/",
        "vehicle_options_module": "regions.ger.data.vehicle_options",
        "language": "de",
    },
    "nld": {
        "display_name": "Netherlands",
        "base_url": "https://www.meldkamerspel.com/",
        "vehicle_options_module": "regions.nld.data.vehicle_options",
        "language": "nl",
    },
    "swe": {
        "display_name": "Sweden",
        "base_url": "https://www.larmcentralen-spelet.se/",
        "vehicle_options_module": "regions.swe.data.vehicle_options",
        "language": "sv",
    },
    "pt": {
        "display_name": "Portugal",
        "base_url": "https://www.jogo-operador112.com/",
        "vehicle_options_module": "regions.pt.data.vehicle_options",
        "language": "pt",
    },
    "dk": {
        "display_name": "Denmark",
        "base_url": "https://www.alarmcentral-spil.dk/",
        "vehicle_options_module": "regions.dk.data.vehicle_options",
        "language": "da",
    },
}

_REGION_ALIASES = {
    "america": "us",
    "usa": "us",
    "united states": "us",
    "gb": "uk",
    "england": "uk",
    "united kingdom": "uk",
    "australia": "aus",
    "au": "aus",
    "germany": "ger",
    "de": "ger",
    "netherlands": "nld",
    "nl": "nld",
    "se": "swe",
    "sweden": "swe",
    "sv": "swe",
    "portugal": "pt",
    "pt-pt": "pt",
    "denmark": "dk",
    "danish": "dk",
    "dk": "dk",
}


def supported_regions() -> tuple[str, ...]:
    return tuple(_REGION_DEFINITIONS)


def get_region_profile(region: str | None = None) -> RegionProfile:
    if region is None:
        from .settings import get_settings

        region = get_settings().region
    key = _REGION_ALIASES.get(region.strip().lower(), region.strip().lower())
    try:
        definition = _REGION_DEFINITIONS[key]
    except KeyError as error:
        choices = ", ".join(supported_regions())
        raise ValueError(
            f"Unsupported MissionChief region {region!r}. Choose one of: {choices}. "
            "There is no dedicated MissionChief adapter for that region."
        ) from error
    return RegionProfile(
        key=key,
        display_name=definition["display_name"],
        base_url=definition["base_url"],
        runtime_supported=True,
        data_dir=PROJECT_ROOT / "regions" / key / "data",
        vehicle_options_module=definition["vehicle_options_module"],
        language=definition["language"],
        notes=definition.get("notes", ""),
    )
