import json
from pathlib import Path

import pytest

from core import update_checker
from core.update_checker import (
    check_for_updates,
    current_version,
    newer_release,
    parse_version,
    summarize_changes,
)

RELEASE_BODY = """## [3.3.1](https://github.com/NatesHonor/MissionchiefBot-X/compare/v3.3.0...v3.3.1) (2026-10-20)


### Bug Fixes

* dispatch localized personnel requirements by vehicle crew ([#100](https://github.com/NatesHonor/MissionchiefBot-X/issues/100)) ([abc1234](https://github.com/NatesHonor/MissionchiefBot-X/commit/abc1234def))
* **deps:** bump actions/setup-python from 5 to 7 ([#98](https://github.com/NatesHonor/MissionchiefBot-X/issues/98)) ([ce79dbf](https://github.com/NatesHonor/MissionchiefBot-X/commit/ce79dbf))
"""


def _release(tag: str = "v3.3.1", **extra: object) -> dict:
    return {"tag_name": tag, "html_url": f"https://github.com/x/y/releases/tag/{tag}", "body": RELEASE_BODY, **extra}


def test_parse_version() -> None:
    assert parse_version("v3.3.1") == (3, 3, 1)
    assert parse_version("3.10.0") == (3, 10, 0)
    assert parse_version("nope") is None


def test_current_version_reads_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / ".release-please-manifest.json"
    manifest.write_text(json.dumps({".": "3.3.0"}))
    assert current_version(manifest) == "3.3.0"
    assert current_version(tmp_path / "missing.json") is None


def test_newer_release_only_when_newer() -> None:
    assert newer_release("3.3.0", _release("v3.3.1"))
    assert newer_release("3.3.1", _release("v3.3.1")) is None
    assert newer_release("3.4.0", _release("v3.3.1")) is None
    assert newer_release("3.9.0", _release("v3.10.0"))
    assert newer_release("3.3.0", _release("v3.3.1", prerelease=True)) is None
    assert newer_release("3.3.0", None) is None


def test_summary_strips_links_and_hashes() -> None:
    assert summarize_changes(RELEASE_BODY) == [
        "dispatch localized personnel requirements by vehicle crew",
        "deps: bump actions/setup-python from 5 to 7",
    ]


def test_summary_is_capped() -> None:
    body = "\n".join(f"* change {n}" for n in range(12))
    lines = summarize_changes(body, limit=3)
    assert lines == ["change 0", "change 1", "change 2", "...and 9 more"]


def _setup(monkeypatch: pytest.MonkeyPatch, installed: str, release: dict | None) -> None:
    monkeypatch.delenv("MISSIONCHIEF_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(update_checker, "current_version", lambda: installed)
    monkeypatch.setattr(update_checker, "fetch_latest_release", lambda: release)


def test_shows_notice_and_waits_when_update_available(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _setup(monkeypatch, "3.3.0", _release("v3.3.1"))
    waits: list[float] = []
    assert check_for_updates(sleep=waits.append) is True
    assert waits == [update_checker.NOTICE_SECONDS]
    output = capsys.readouterr().out
    assert "3.3.1" in output
    assert "dispatch localized personnel requirements" in output


def test_no_notice_or_wait_when_up_to_date(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "3.3.1", _release("v3.3.1"))
    waits: list[float] = []
    assert check_for_updates(sleep=waits.append) is False
    assert waits == []


def test_github_failure_never_blocks_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "3.3.0", None)
    waits: list[float] = []
    assert check_for_updates(sleep=waits.append) is False
    assert waits == []


def test_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "3.3.0", _release("v3.3.1"))
    monkeypatch.setenv("MISSIONCHIEF_UPDATE_CHECK", "false")
    waits: list[float] = []
    assert check_for_updates(sleep=waits.append) is False
    assert waits == []
