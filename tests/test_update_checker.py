import json
from collections.abc import Callable
from pathlib import Path

import pytest

from core import update_checker
from core.auto_updater import UpdateError
from core.update_checker import (
    ask_yes_no,
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


def _answers(*values: str) -> Callable[[str], str]:
    queue = list(values)

    def read(_prompt: str) -> str:
        return queue.pop(0)

    return read


def test_ask_yes_no() -> None:
    assert ask_yes_no("?", _answers("y")) is True
    assert ask_yes_no("?", _answers("YES")) is True
    assert ask_yes_no("?", _answers("n")) is False
    assert ask_yes_no("?", _answers("")) is False
    assert ask_yes_no("?", _answers("maybe", "y")) is True


def test_ask_yes_no_treats_eof_as_no() -> None:
    def read(_prompt: str) -> str:
        raise EOFError

    assert ask_yes_no("?", read) is False


class _Recorder:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[tuple[dict, str]] = []
        self.error = error

    def __call__(self, release: dict, installed: str) -> None:
        self.calls.append((release, installed))
        if self.error:
            raise self.error


def _setup(monkeypatch: pytest.MonkeyPatch, installed: str, release: dict | None, blocked: str | None = None) -> None:
    monkeypatch.delenv("MISSIONCHIEF_UPDATE_CHECK", raising=False)
    monkeypatch.delenv("MISSIONCHIEF_AUTO_UPDATE", raising=False)
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.setattr(update_checker, "load_dotenv", lambda: None, raising=False)
    monkeypatch.setattr(update_checker, "current_version", lambda: installed)
    monkeypatch.setattr(update_checker, "fetch_latest_release", lambda: release)
    monkeypatch.setattr(update_checker, "can_self_update", lambda: blocked)


def test_yes_installs_update(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _setup(monkeypatch, "3.3.0", _release("v3.3.1"))
    update = _Recorder()
    assert check_for_updates(read=_answers("y"), interactive=lambda: True, update=update) is True
    assert update.calls and update.calls[0][1] == "3.3.0"
    output = capsys.readouterr().out
    assert "3.3.1" in output
    assert "dispatch localized personnel requirements" in output


def test_no_skips_update(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "3.3.0", _release("v3.3.1"))
    update = _Recorder()
    assert check_for_updates(read=_answers("n"), interactive=lambda: True, update=update) is False
    assert update.calls == []


def test_no_prompt_without_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "3.3.0", _release("v3.3.1"))
    update = _Recorder()

    def read(_prompt: str) -> str:
        raise AssertionError("must not prompt without a terminal")

    assert check_for_updates(read=read, interactive=lambda: False, update=update) is False
    assert update.calls == []


def test_auto_update_env_skips_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "3.3.0", _release("v3.3.1"))
    monkeypatch.setenv("MISSIONCHIEF_AUTO_UPDATE", "true")
    update = _Recorder()
    assert check_for_updates(read=_answers(), interactive=lambda: False, update=update) is True
    assert len(update.calls) == 1


def test_blocked_install_only_shows_notice(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _setup(monkeypatch, "3.3.0", _release("v3.3.1"), blocked="This is a git checkout. Update with: git pull")
    update = _Recorder()
    assert check_for_updates(read=_answers("y"), interactive=lambda: True, update=update) is False
    assert update.calls == []
    assert "git pull" in capsys.readouterr().out


def test_failed_update_keeps_running(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _setup(monkeypatch, "3.3.0", _release("v3.3.1"))
    update = _Recorder(UpdateError("Download failed"))
    assert check_for_updates(read=_answers("y"), interactive=lambda: True, update=update) is False
    assert "Download failed" in capsys.readouterr().out


def test_nothing_happens_when_up_to_date(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "3.3.1", _release("v3.3.1"))
    update = _Recorder()
    assert check_for_updates(read=_answers(), interactive=lambda: True, update=update) is False
    assert update.calls == []


def test_offline_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "3.3.0", None)
    assert check_for_updates(read=_answers(), interactive=lambda: True, update=_Recorder()) is False


def test_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup(monkeypatch, "3.3.0", _release("v3.3.1"))
    monkeypatch.setenv("MISSIONCHIEF_UPDATE_CHECK", "false")
    update = _Recorder()
    assert check_for_updates(read=_answers(), interactive=lambda: True, update=update) is False
    assert update.calls == []
