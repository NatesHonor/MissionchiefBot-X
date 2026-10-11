from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXACT_PIN = re.compile(r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[^=\s]+$")


def _requirement_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "-r "))
    ]


def test_runtime_dependencies_are_exactly_pinned() -> None:
    requirements = _requirement_lines(PROJECT_ROOT / "requirements.txt")
    assert requirements
    assert all(EXACT_PIN.fullmatch(requirement) for requirement in requirements)


def test_playwright_versions_match_container() -> None:
    requirements = _requirement_lines(PROJECT_ROOT / "requirements.txt")
    playwright_pin = next(line.split("==", 1)[1] for line in requirements if line.startswith("playwright=="))
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert f"playwright/python:v{playwright_pin}-" in dockerfile


def test_public_runtime_config_is_safe() -> None:
    config = (PROJECT_ROOT / "config.ini.example").read_text(encoding="utf-8")
    assert "username =\n" in config
    assert "password =\n" in config
    assert "host = 127.0.0.1" in config
