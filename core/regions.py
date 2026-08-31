"""Region metadata and per-region data locations."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RegionProfile:
    key: str
    base_url: str
    runtime_supported: bool
    data_dir: Path
    vehicle_options_module: str
    language: str = "en"

    @property
    def login_url(self) -> str:
        return f"{self.base_url}users/sign_in"

    @property
    def mission_file(self) -> Path:
        return self.data_dir / "mission_data.json"

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

    def ensure_data_dir(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir

    def vehicle_options(self, vehicle_type: str) -> list[str]:
        module = importlib.import_module(self.vehicle_options_module)
        return module.get_vehicle_options(vehicle_type)


_REGION_DEFINITIONS = {
    "us": ("https://www.missionchief.com/", True, "utils.vehicle_options", "en"),
    "uk": ("https://www.missionchief.co.uk/", True, "regions.uk.data.vehicle_options", "en"),
    "aus": ("https://www.missionchief-australia.com/", False, "utils.vehicle_options", "en"),
    "ger": ("https://www.leitstellenspiel.de/", True, "regions.ger.data.vehicle_options", "de"),
    "nld": ("https://www.meldkamerspel.com/", False, "utils.vehicle_options", "nl"),
    "swe": (
        "https://www.larmcentralen-spelet.se/",
        True,
        "regions.swe.data.vehicle_options",
        "sv",
    ),
}

_REGION_ALIASES = {"se": "swe", "sweden": "swe"}


def supported_regions() -> tuple[str, ...]:
    return tuple(_REGION_DEFINITIONS)


def get_region_profile(region: str | None = None) -> RegionProfile:
    if region is None:
        from .settings import get_settings

        region = get_settings().region
    key = _REGION_ALIASES.get(region.strip().lower(), region.strip().lower())
    try:
        base_url, runtime_supported, options_module, language = _REGION_DEFINITIONS[key]
    except KeyError as error:
        choices = ", ".join(supported_regions())
        raise ValueError(f"Unsupported MissionChief region {region!r}. Choose one of: {choices}.") from error
    return RegionProfile(
        key=key,
        base_url=base_url,
        runtime_supported=runtime_supported,
        data_dir=PROJECT_ROOT / "regions" / key / "data",
        vehicle_options_module=options_module,
        language=language,
    )
