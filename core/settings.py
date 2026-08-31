"""Typed configuration loading with environment overrides.

Configuration is deliberately loaded on demand.  Importing a module should
not read credentials, depend on the current working directory, or freeze the
selected region before the application starts.
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.ini"


@dataclass(frozen=True)
class TrainingPlan:
    """One configured school course and its maximum simultaneous rooms."""

    school: str
    course: str
    rooms: int = 1


@dataclass(frozen=True)
class Settings:
    username: str
    password: str
    region: str
    headless: bool
    browsers: int
    browser_scaling: bool
    dispatch_type: str
    dispatch_by_distance: bool
    dispatch_incomplete: bool
    dynamic_missions: bool
    concurrent_missions: bool
    auto_training: bool
    auto_recruiting: bool
    auto_tasks: bool
    dynamic_delays: bool
    dynamic_delay_missions: bool
    dynamic_delay_transport: bool
    mission_delay: int
    other_delay: int
    training_plans: tuple[TrainingPlan, ...] = ()
    recruiting_days: int = 1


def _config_path(path: str | os.PathLike[str] | None = None) -> Path:
    configured = path or os.getenv("MISSIONCHIEF_CONFIG_FILE")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_CONFIG_PATH


def _read_config(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(path)
    return parser


def _value(
    parser: configparser.ConfigParser,
    path: Path,
    section: str,
    option: str,
    environment_name: str,
    default: str | None = None,
) -> str:
    environment_value = os.getenv(environment_name)
    if environment_value is not None:
        return environment_value
    try:
        return parser.get(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError) as error:
        if default is not None:
            return default
        raise RuntimeError(
            f"Missing configuration value [{section}] {option}. "
            f"Set {environment_name} or add it to {path}."
        ) from error


def _required(value: str, environment_name: str) -> str:
    value = value.strip()
    if not value:
        raise RuntimeError(f"{environment_name} must not be empty.")
    return value


def _boolean(value: str, environment_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "yes", "true", "on"}:
        return True
    if normalized in {"0", "no", "false", "off"}:
        return False
    raise ValueError(
        f"Invalid boolean value for {environment_name}: {value!r}. Use true/false."
    )


def _integer(value: str, environment_name: str, minimum: int | None = None) -> int:
    try:
        parsed = int(value.strip())
    except ValueError as error:
        raise ValueError(
            f"Invalid integer value for {environment_name}: {value!r}."
        ) from error
    if minimum is not None and parsed < minimum:
        raise ValueError(
            f"Invalid value for {environment_name}: {parsed}. "
            f"It must be at least {minimum}."
        )
    return parsed


def _training_plans(parser: configparser.ConfigParser, path: Path) -> tuple[TrainingPlan, ...]:
    plans = []
    for section in parser.sections():
        if not section.casefold().startswith("trainings."):
            continue
        fallback_school = section.split(".", 1)[1].replace("_", " ").strip().title()
        school = parser.get(section, "school", fallback=fallback_school).strip()
        course = parser.get(section, "training", fallback="").strip()
        if not school or not course:
            continue
        rooms = _integer(
            parser.get(section, "rooms", fallback="1"),
            f"[{section}] rooms in {path}",
            minimum=1,
        )
        plans.append(TrainingPlan(school=school, course=course, rooms=rooms))
    return tuple(plans)


def load_settings(path: str | os.PathLike[str] | None = None) -> Settings:
    """Load one complete, validated settings snapshot."""

    config_file = _config_path(path)
    parser = _read_config(config_file)

    return Settings(
        username=_required(
            _value(parser, config_file, "credentials", "username", "MISSIONCHIEF_USERNAME"),
            "MISSIONCHIEF_USERNAME",
        ),
        password=_required(
            _value(parser, config_file, "credentials", "password", "MISSIONCHIEF_PASSWORD"),
            "MISSIONCHIEF_PASSWORD",
        ),
        region=_value(parser, config_file, "bot", "region", "MISSIONCHIEF_REGION")
        .strip()
        .lower(),
        headless=_boolean(
            _value(parser, config_file, "browser_settings", "headless", "MISSIONCHIEF_HEADLESS"),
            "MISSIONCHIEF_HEADLESS",
        ),
        browsers=_integer(
            _value(parser, config_file, "browser_settings", "browsers", "MISSIONCHIEF_BROWSERS"),
            "MISSIONCHIEF_BROWSERS",
            minimum=1,
        ),
        browser_scaling=_boolean(
            _value(
                parser,
                config_file,
                "browser_settings",
                "browser_scaling",
                "MISSIONCHIEF_BROWSER_SCALING",
            ),
            "MISSIONCHIEF_BROWSER_SCALING",
        ),
        dispatch_type=_value(parser, config_file, "missions", "dispatch", "MISSIONCHIEF_DISPATCH").strip(),
        dispatch_by_distance=_boolean(
            _value(
                parser,
                config_file,
                "missions",
                "dispatch_vehicles_by_distance",
                "MISSIONCHIEF_DISPATCH_VEHICLES_BY_DISTANCE",
            ),
            "MISSIONCHIEF_DISPATCH_VEHICLES_BY_DISTANCE",
        ),
        dispatch_incomplete=_boolean(
            _value(
                parser,
                config_file,
                "missions",
                "dispatch_incomplete_missions",
                "MISSIONCHIEF_DISPATCH_INCOMPLETE_MISSIONS",
            ),
            "MISSIONCHIEF_DISPATCH_INCOMPLETE_MISSIONS",
        ),
        dynamic_missions=_boolean(
            _value(
                parser,
                config_file,
                "missions",
                "dynamic_missions",
                "MISSIONCHIEF_DYNAMIC_MISSIONS",
                default="false",
            ),
            "MISSIONCHIEF_DYNAMIC_MISSIONS",
        ),
        concurrent_missions=_boolean(
            _value(
                parser,
                config_file,
                "missions",
                "dispatch_concurrent_missions",
                "MISSIONCHIEF_DISPATCH_CONCURRENT_MISSIONS",
            ),
            "MISSIONCHIEF_DISPATCH_CONCURRENT_MISSIONS",
        ),
        auto_training=_boolean(
            _value(parser, config_file, "other", "auto_training", "MISSIONCHIEF_AUTO_TRAINING"),
            "MISSIONCHIEF_AUTO_TRAINING",
        ),
        auto_recruiting=_boolean(
            _value(
                parser,
                config_file,
                "other",
                "auto_recruiting",
                "MISSIONCHIEF_AUTO_RECRUITING",
                default="false",
            ),
            "MISSIONCHIEF_AUTO_RECRUITING",
        ),
        auto_tasks=_boolean(
            _value(parser, config_file, "other", "auto_tasks", "MISSIONCHIEF_AUTO_TASKS"),
            "MISSIONCHIEF_AUTO_TASKS",
        ),
        dynamic_delays=_boolean(
            _value(parser, config_file, "delays", "dynamic_delays", "MISSIONCHIEF_DYNAMIC_DELAYS"),
            "MISSIONCHIEF_DYNAMIC_DELAYS",
        ),
        dynamic_delay_missions=_boolean(
            _value(
                parser,
                config_file,
                "delays",
                "dynamic_missions",
                "MISSIONCHIEF_DYNAMIC_DELAY_MISSIONS",
            ),
            "MISSIONCHIEF_DYNAMIC_DELAY_MISSIONS",
        ),
        dynamic_delay_transport=_boolean(
            _value(
                parser,
                config_file,
                "delays",
                "dynamic_transport",
                "MISSIONCHIEF_DYNAMIC_DELAY_TRANSPORT",
                default="false",
            ),
            "MISSIONCHIEF_DYNAMIC_DELAY_TRANSPORT",
        ),
        mission_delay=_integer(
            _value(parser, config_file, "delays", "missions", "MISSIONCHIEF_MISSION_DELAY"),
            "MISSIONCHIEF_MISSION_DELAY",
            minimum=0,
        ),
        other_delay=_integer(
            _value(parser, config_file, "delays", "other", "MISSIONCHIEF_OTHER_DELAY"),
            "MISSIONCHIEF_OTHER_DELAY",
            minimum=0,
        ),
        training_plans=_training_plans(parser, config_file),
        recruiting_days=_integer(
            parser.get("recruiting", "days", fallback="1"),
            "[recruiting] days",
            minimum=1,
        ),
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the process-wide settings snapshot used by compatibility APIs."""

    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def reset_settings() -> None:
    """Clear the compatibility snapshot (useful for tests and process reuse)."""

    global _settings
    _settings = None
