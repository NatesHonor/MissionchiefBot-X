"""Typed settings loaded exclusively from environment variables and `.env`."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
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


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
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


def _training_plans() -> tuple[TrainingPlan, ...]:
    raw = os.getenv("MISSIONCHIEF_TRAINING_PLANS", "[]")
    try:
        values = json.loads(raw)
        return tuple(
            TrainingPlan(
                school=str(item["school"]).strip(),
                course=str(item["course"]).strip(),
                rooms=max(1, int(item.get("rooms", 1))),
            )
            for item in values
        )
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise ValueError("MISSIONCHIEF_TRAINING_PLANS must be a JSON array of school/course/rooms objects.") from error


def load_settings(path: str | os.PathLike[str] | None = None) -> Settings:
    """Load `.env`, apply real environment overrides, and validate one snapshot."""

    load_dotenv(Path(path).expanduser() if path else DEFAULT_ENV_PATH, override=False)
    return Settings(
        username=_required("MISSIONCHIEF_USERNAME"),
        password=_required("MISSIONCHIEF_PASSWORD"),
        region=_text("MISSIONCHIEF_REGION", "uk").lower(),
        headless=_boolean("MISSIONCHIEF_HEADLESS", True),
        browsers=_integer("MISSIONCHIEF_BROWSERS", 3, 2),
        browser_scaling=_boolean("MISSIONCHIEF_BROWSER_SCALING", False),
        dispatch_type=_text("MISSIONCHIEF_DISPATCH", "alliance"),
        dispatch_by_distance=_boolean("MISSIONCHIEF_DISPATCH_VEHICLES_BY_DISTANCE", True),
        dispatch_incomplete=_boolean("MISSIONCHIEF_DISPATCH_INCOMPLETE_MISSIONS", False),
        dynamic_missions=_boolean("MISSIONCHIEF_DYNAMIC_MISSIONS", False),
        include_alliance_missions=_boolean("MISSIONCHIEF_INCLUDE_ALLIANCE_MISSIONS", True),
        max_missions=_integer("MISSIONCHIEF_MAX_MISSIONS", 500),
        concurrent_missions=_boolean("MISSIONCHIEF_DISPATCH_CONCURRENT_MISSIONS", True),
        auto_training=_boolean("MISSIONCHIEF_AUTO_TRAINING", False),
        auto_recruiting=_boolean("MISSIONCHIEF_AUTO_RECRUITING", False),
        auto_special_resources=_boolean("MISSIONCHIEF_AUTO_SPECIAL_RESOURCES", False),
        auto_tasks=_boolean("MISSIONCHIEF_AUTO_TASKS", False),
        dynamic_delays=_boolean("MISSIONCHIEF_DYNAMIC_DELAYS", False),
        dynamic_delay_missions=_boolean("MISSIONCHIEF_DYNAMIC_DELAY_MISSIONS", False),
        dynamic_delay_transport=_boolean("MISSIONCHIEF_DYNAMIC_DELAY_TRANSPORT", False),
        mission_delay=_integer("MISSIONCHIEF_MISSION_DELAY", 10),
        other_delay=_integer("MISSIONCHIEF_OTHER_DELAY", 30),
        dispatch_delay=_integer("MISSIONCHIEF_DISPATCH_DELAY", 0),
        training_plans=_training_plans(),
        recruiting_days=_integer("MISSIONCHIEF_RECRUITING_DAYS", 1, 1),
        version=_text("MISSIONCHIEF_VERSION", "dev"),
        webui_enabled=_boolean("MISSIONCHIEF_WEBUI_ENABLED", False),
        webui_host=_text("MISSIONCHIEF_WEBUI_HOST", "127.0.0.1"),
        webui_port=_integer("MISSIONCHIEF_WEBUI_PORT", 8765, 1),
        log_level=_text("MISSIONCHIEF_LOG_LEVEL", "INFO").upper(),
        log_console=_boolean("MISSIONCHIEF_LOG_CONSOLE", True),
        log_file_enabled=_boolean("MISSIONCHIEF_LOG_FILE_ENABLED", True),
        log_rich_console=_boolean("MISSIONCHIEF_LOG_RICH_CONSOLE", True),
        log_file=_text("MISSIONCHIEF_LOG_FILE", "logs/missionchiefbot.log"),
        log_max_bytes=_integer("MISSIONCHIEF_LOG_MAX_BYTES", 5 * 1024 * 1024, 1024),
        log_backup_count=_integer("MISSIONCHIEF_LOG_BACKUP_COUNT", 5),
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
