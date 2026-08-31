"""Central region registry and localized data access.

The MissionChief websites share most of their HTML and API contracts, but the
vehicle names, requirement labels, and language-specific text do not.  Every
runtime component receives a :class:`RegionProfile` instead of making its own
region assumptions.
"""

from __future__ import annotations

import importlib
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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

    def vehicle_options(self, vehicle_type: str) -> list[str]:
        module = importlib.import_module(self.vehicle_options_module)
        options = list(module.get_vehicle_options(vehicle_type) or [])
        if options:
            return list(dict.fromkeys(options))

        # Aliases are data, not code.  This fallback lets a regional page use
        # a localized requirement label even when the shared canonical name is
        # requested by the dispatcher.
        def normalize(value):
            value = unicodedata.normalize("NFKD", str(value or ""))
            value = "".join(character for character in value if not unicodedata.combining(character))
            return " ".join(value.casefold().replace("-", " ").split())

        requested = normalize(vehicle_type)
        aliases = self.vehicle_aliases()
        for canonical, synonyms in aliases.items():
            values = [canonical, *(synonyms if isinstance(synonyms, list) else [])]
            if requested in {normalize(value) for value in values}:
                return list(dict.fromkeys(values[1:] or [canonical]))
        return []


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
