"""Typed configuration loaded from `.env` and process environment."""

from __future__ import annotations

import json
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class TrainingPlan:
    school: str
    course: str
    rooms: int = 1


@dataclass(frozen=True)
class Settings:
    username: str
    password: str
    region: str = "uk"
    headless: bool = True
    browsers: int = 3
    browser_scaling: bool = False
    dispatch_type: str = "alliance"
    dispatch_by_distance: bool = True
    dispatch_incomplete: bool = False
    dynamic_missions: bool = False
    include_alliance_missions: bool = True
    max_missions: int = 500
    concurrent_missions: bool = True
    auto_training: bool = False
    auto_recruiting: bool = False
    auto_special_resources: bool = False
    auto_tasks: bool = False
    dynamic_delays: bool = False
    dynamic_delay_missions: bool = False
    dynamic_delay_transport: bool = False
    mission_delay: int = 10
    other_delay: int = 30
    dispatch_delay: int = 0
    training_plans: tuple[TrainingPlan, ...] = ()
    recruiting_days: int = 1
    version: str = "dev"
    webui_enabled: bool = False
    webui_host: str = "127.0.0.1"
    webui_port: int = 8765
    log_level: str = "INFO"
    log_console: bool = True
    log_file_enabled: bool = True
    log_rich_console: bool = True
    log_file: str = "logs/missionchiefbot.log"
    log_max_bytes: int = 5 * 1024 * 1024
    log_backup_count: int = 5


def _env_path(path: str | os.PathLike[str] | None = None) -> Path:
    configured = path or os.getenv("MISSIONCHIEF_ENV_FILE")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_ENV_PATH


def _value(
    source: dict[str, str | None],
    path: Path,
    _section: str,
    _option: str,
    environment_name: str,
    default: str | None = None,
) -> str:
    environment_value = os.getenv(environment_name)
    if environment_value is not None:
        return environment_value
    file_value = source.get(environment_name)
    if file_value is not None:
        return file_value
    if default is not None:
        return default
    raise RuntimeError(f"Missing {environment_name}. Add it to {path} or set it in the process environment.")


def _required(value: str, environment_name: str) -> str:
    value = value.strip()
    if not value:
        raise RuntimeError(f"{name} must be set in .env or the process environment.")
    return value


def _text(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _boolean(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "yes", "true", "on"}:
        return True
    if normalized in {"0", "no", "false", "off"}:
        return False
    raise ValueError(f"Invalid boolean for {name}: {value!r}. Use true or false.")


def _integer(name: str, default: int, minimum: int = 0) -> int:
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"Invalid integer for {name}: {value!r}.") from error
    if parsed < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return parsed


def _training_plans(value: str, path: Path) -> tuple[TrainingPlan, ...]:
    try:
        entries = json.loads(value)
        return tuple(
            TrainingPlan(
                school=_required(str(entry["school"]), "school"),
                course=_required(str(entry["course"]), "course"),
                rooms=_integer(str(entry.get("rooms", 1)), "rooms", minimum=1),
            )
            for entry in entries
        )
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid MISSIONCHIEF_TRAINING_PLANS in {path}; expected a JSON array.") from error


def load_settings(path: str | os.PathLike[str] | None = None) -> Settings:
    """Load one complete, validated settings snapshot from a dotenv file."""

    env_file = _env_path(path)
    parser = dict(dotenv_values(env_file))
    config_file = env_file

    return Settings(
        username=_required(
            _value(parser, config_file, "credentials", "username", "MISSIONCHIEF_USERNAME"),
            "MISSIONCHIEF_USERNAME",
        ),
        password=_required(
            _value(parser, config_file, "credentials", "password", "MISSIONCHIEF_PASSWORD"),
            "MISSIONCHIEF_PASSWORD",
        ),
        region=_value(parser, config_file, "bot", "region", "MISSIONCHIEF_REGION").strip().lower(),
        headless=_boolean(
            _value(parser, config_file, "browser_settings", "headless", "MISSIONCHIEF_HEADLESS"),
            "MISSIONCHIEF_HEADLESS",
        ),
        browsers=_integer(
            _value(parser, config_file, "browser_settings", "browsers", "MISSIONCHIEF_BROWSERS"),
            "MISSIONCHIEF_BROWSERS",
            minimum=2,
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
        include_alliance_missions=_boolean(
            _value(
                parser,
                config_file,
                "missions",
                "include_alliance_missions",
                "MISSIONCHIEF_INCLUDE_ALLIANCE_MISSIONS",
                default="true",
            ),
            "MISSIONCHIEF_INCLUDE_ALLIANCE_MISSIONS",
        ),
        max_missions=_integer(
            _value(
                parser,
                config_file,
                "missions",
                "max_missions",
                "MISSIONCHIEF_MAX_MISSIONS",
                default="500",
            ),
            "MISSIONCHIEF_MAX_MISSIONS",
            minimum=0,
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
        auto_special_resources=_boolean(
            _value(
                parser,
                config_file,
                "other",
                "auto_special_resources",
                "MISSIONCHIEF_AUTO_SPECIAL_RESOURCES",
                default="false",
            ),
            "MISSIONCHIEF_AUTO_SPECIAL_RESOURCES",
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
        dispatch_delay=_integer(
            _value(
                parser,
                config_file,
                "delays",
                "dispatch",
                "MISSIONCHIEF_DISPATCH_DELAY",
                default="0",
            ),
            "MISSIONCHIEF_DISPATCH_DELAY",
            minimum=0,
        ),
        training_plans=_training_plans(
            _value(
                parser,
                config_file,
                "training",
                "plans",
                "MISSIONCHIEF_TRAINING_PLANS",
                default="[]",
            ),
            config_file,
        ),
        recruiting_days=_integer(
            _value(
                parser,
                config_file,
                "recruiting",
                "days",
                "MISSIONCHIEF_RECRUITING_DAYS",
                default="1",
            ),
            "MISSIONCHIEF_RECRUITING_DAYS",
            minimum=1,
        ),
        version=_value(
            parser,
            config_file,
            "bot",
            "version",
            "MISSIONCHIEF_VERSION",
            default="dev",
        ).strip(),
        webui_enabled=_boolean(
            _value(
                parser,
                config_file,
                "webui",
                "enabled",
                "MISSIONCHIEF_WEBUI_ENABLED",
                default="false",
            ),
            "MISSIONCHIEF_WEBUI_ENABLED",
        ),
        webui_host=_value(
            parser,
            config_file,
            "webui",
            "host",
            "MISSIONCHIEF_WEBUI_HOST",
            default="127.0.0.1",
        ).strip(),
        webui_port=_integer(
            _value(
                parser,
                config_file,
                "webui",
                "port",
                "MISSIONCHIEF_WEBUI_PORT",
                default="8765",
            ),
            "MISSIONCHIEF_WEBUI_PORT",
            minimum=1,
        ),
        log_level=_value(parser, config_file, "logging", "level", "MISSIONCHIEF_LOG_LEVEL", default="INFO")
        .strip()
        .upper(),
        log_console=_boolean(
            _value(parser, config_file, "logging", "console", "MISSIONCHIEF_LOG_CONSOLE", default="true"),
            "MISSIONCHIEF_LOG_CONSOLE",
        ),
        log_file_enabled=_boolean(
            _value(parser, config_file, "logging", "file", "MISSIONCHIEF_LOG_FILE_ENABLED", default="true"),
            "MISSIONCHIEF_LOG_FILE_ENABLED",
        ),
        log_rich_console=_boolean(
            _value(parser, config_file, "logging", "rich_console", "MISSIONCHIEF_LOG_RICH_CONSOLE", default="true"),
            "MISSIONCHIEF_LOG_RICH_CONSOLE",
        ),
        log_file=_value(
            parser,
            config_file,
            "logging",
            "path",
            "MISSIONCHIEF_LOG_FILE",
            default="logs/missionchiefbot.log",
        ).strip(),
        log_max_bytes=_integer(
            _value(parser, config_file, "logging", "max_bytes", "MISSIONCHIEF_LOG_MAX_BYTES", default="5242880"),
            "MISSIONCHIEF_LOG_MAX_BYTES",
            minimum=1024,
        ),
        log_backup_count=_integer(
            _value(parser, config_file, "logging", "backup_count", "MISSIONCHIEF_LOG_BACKUP_COUNT", default="5"),
            "MISSIONCHIEF_LOG_BACKUP_COUNT",
            minimum=0,
        ),
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None
