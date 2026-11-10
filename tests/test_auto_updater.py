import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from core import auto_updater
from core.auto_updater import (
    UpdateError,
    backup_install,
    extract_release,
    install_files,
    migrate_env,
    parse_env,
    perform_update,
    restore_backup,
)

TEMPLATE = """# Bot
MISSIONCHIEF_VERSION=3.4.0
MISSIONCHIEF_REGION=UK

# New in this version
MISSIONCHIEF_NEW_FEATURE=false
MISSIONCHIEF_PASSWORD=
"""

OLD_ENV = """MISSIONCHIEF_VERSION=3.3.0
MISSIONCHIEF_REGION=DE
MISSIONCHIEF_PASSWORD="p@ss=word # not a comment"
MISSIONCHIEF_REMOVED_SETTING=42
"""


def test_parse_env_keeps_values_verbatim() -> None:
    values = parse_env(OLD_ENV + "# MISSIONCHIEF_COMMENTED=1\nexport FOO=bar\n")
    assert values["MISSIONCHIEF_PASSWORD"] == '"p@ss=word # not a comment"'
    assert values["FOO"] == "bar"
    assert "MISSIONCHIEF_COMMENTED" not in values


def test_migrate_env_keeps_user_values_and_adds_new_ones() -> None:
    migrated = migrate_env(OLD_ENV, TEMPLATE, "3.4.0")
    values = parse_env(migrated)
    assert values["MISSIONCHIEF_VERSION"] == "3.4.0"
    assert values["MISSIONCHIEF_REGION"] == "DE"
    assert values["MISSIONCHIEF_PASSWORD"] == '"p@ss=word # not a comment"'
    assert values["MISSIONCHIEF_NEW_FEATURE"] == "false"
    assert values["MISSIONCHIEF_REMOVED_SETTING"] == "42"
    assert "# New in this version" in migrated
    assert migrated.index("MISSIONCHIEF_NEW_FEATURE") < migrated.index("MISSIONCHIEF_REMOVED_SETTING")


def test_migrate_env_without_old_env_uses_template() -> None:
    assert parse_env(migrate_env("", TEMPLATE, "3.4.0")) == parse_env(TEMPLATE)


def _make_install(root: Path) -> None:
    (root / "core").mkdir(parents=True)
    (root / "Main.py").write_text("old main")
    (root / "core" / "old_module.py").write_text("old")
    (root / ".env").write_text(OLD_ENV)
    (root / "config.ini").write_text("[user]")
    (root / "data").mkdir()
    (root / "data" / "missionchief.sqlite3").write_text("db")
    (root / "logs").mkdir()
    (root / "logs" / "latest.log").write_text("log")


def _make_release(source: Path) -> None:
    (source / "core").mkdir(parents=True)
    (source / "Main.py").write_text("new main")
    (source / "core" / "new_module.py").write_text("new")
    (source / ".env.example").write_text(TEMPLATE)


def test_install_replaces_code_but_keeps_user_data(tmp_path: Path) -> None:
    root, source = tmp_path / "install", tmp_path / "release"
    _make_install(root)
    _make_release(source)
    install_files(source, root)
    assert (root / "Main.py").read_text() == "new main"
    assert (root / "core" / "new_module.py").exists()
    assert not (root / "core" / "old_module.py").exists()
    assert (root / ".env").read_text() == OLD_ENV
    assert (root / "config.ini").exists()
    assert (root / "data" / "missionchief.sqlite3").read_text() == "db"
    assert (root / "logs" / "latest.log").exists()


def test_backup_and_restore_round_trip(tmp_path: Path) -> None:
    root, source = tmp_path / "install", tmp_path / "release"
    _make_install(root)
    _make_release(source)
    backup = backup_install(root, "3.3.0")
    install_files(source, root)
    (root / ".env").write_text("broken")
    restore_backup(root, backup)
    assert (root / "Main.py").read_text() == "old main"
    assert (root / "core" / "old_module.py").exists()
    assert not (root / "core" / "new_module.py").exists()
    assert (root / ".env").read_text() == OLD_ENV
    assert (root / "data" / "missionchief.sqlite3").read_text() == "db"


def _zip_release(path: Path, members: dict[str, str]) -> Path:
    with zipfile.ZipFile(path, "w") as bundle:
        for name, content in members.items():
            bundle.writestr(name, content)
    return path


def test_extract_release_unwraps_github_folder(tmp_path: Path) -> None:
    archive = _zip_release(tmp_path / "r.zip", {"owner-repo-abc/Main.py": "x", "owner-repo-abc/core/a.py": "y"})
    source = extract_release(archive, tmp_path)
    assert (source / "Main.py").read_text() == "x"


def test_extract_release_rejects_path_traversal(tmp_path: Path) -> None:
    archive = _zip_release(tmp_path / "r.zip", {"Main.py": "x", "../evil.py": "y"})
    with pytest.raises(UpdateError):
        extract_release(archive, tmp_path)


def test_extract_release_rejects_unrelated_archive(tmp_path: Path) -> None:
    archive = _zip_release(tmp_path / "r.zip", {"something/else.txt": "x"})
    with pytest.raises(UpdateError):
        extract_release(archive, tmp_path)


def _fake_download(tmp_path: Path, members: dict[str, str]) -> Callable[..., Path]:
    def download(url: str, destination: Path, timeout: float = 60.0) -> Path:
        return _zip_release(destination / "release.zip", members)

    return download


def test_perform_update_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "install"
    _make_install(root)
    monkeypatch.setattr(auto_updater, "can_self_update", lambda root: None)
    monkeypatch.setattr(
        auto_updater,
        "download_release",
        _fake_download(tmp_path, {"r-abc/Main.py": "new main", "r-abc/.env.example": TEMPLATE}),
    )
    release = {"tag_name": "v3.4.0", "zipball_url": "https://example.invalid/zip"}
    perform_update(release, "3.3.0", root=root, log=lambda _m: None, install_deps=False)

    assert (root / "Main.py").read_text() == "new main"
    values = parse_env((root / ".env").read_text())
    assert values["MISSIONCHIEF_VERSION"] == "3.4.0"
    assert values["MISSIONCHIEF_REGION"] == "DE"
    assert values["MISSIONCHIEF_NEW_FEATURE"] == "false"
    assert (root / ".update-backup" / "3.3.0" / "Main.py").read_text() == "old main"
    assert (root / ".update-backup" / "3.3.0" / ".env").read_text() == OLD_ENV


def test_perform_update_restores_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "install"
    _make_install(root)
    monkeypatch.setattr(auto_updater, "can_self_update", lambda root: None)
    monkeypatch.setattr(auto_updater, "download_release", _fake_download(tmp_path, {"r-abc/Main.py": "new main"}))

    def broken_migrate(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(auto_updater, "migrate_env_file", broken_migrate)
    release = {"tag_name": "v3.4.0", "zipball_url": "https://example.invalid/zip"}
    with pytest.raises(UpdateError):
        perform_update(release, "3.3.0", root=root, log=lambda _m: None, install_deps=False)
    assert (root / "Main.py").read_text() == "old main"
    assert (root / ".env").read_text() == OLD_ENV


def test_perform_update_refuses_git_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auto_updater, "in_docker", lambda: False)
    root = tmp_path / "install"
    _make_install(root)
    (root / ".git").mkdir()
    with pytest.raises(UpdateError, match="git pull"):
        perform_update({"tag_name": "v3.4.0", "zipball_url": "https://x"}, "3.3.0", root=root, install_deps=False)


def test_download_requires_https(tmp_path: Path) -> None:
    with pytest.raises(UpdateError):
        auto_updater.download_release("http://example.com/x.zip", tmp_path)
