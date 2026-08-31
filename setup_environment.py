"""Create a runnable virtual environment and provision Playwright Chromium."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import venv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"


def venv_python() -> Path:
    """Return the platform-specific interpreter inside the project venv."""

    relative = Path("Scripts/python.exe") if sys.platform == "win32" else Path("bin/python")
    return VENV_DIR / relative


def run(command: list[str]) -> None:
    """Run one setup command from the repository root."""

    print(f"> {' '.join(command)}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def ensure_virtual_environment() -> Path:
    """Create the project venv when needed and return its interpreter."""

    python = venv_python()
    if not python.is_file():
        print(f"Creating virtual environment at {VENV_DIR}")
        venv.EnvBuilder(with_pip=True, clear=False, upgrade=False).create(VENV_DIR)
    if not python.is_file():
        raise RuntimeError(f"Virtual environment interpreter was not created: {python}")
    return python


def verify_playwright(python: Path) -> None:
    """Verify both the Python package and the installed Chromium executable."""

    try:
        run([str(python), "-c", "import playwright; print('Playwright Python package: available')"])
    except subprocess.CalledProcessError as error:
        raise RuntimeError("Playwright Python package is unavailable.") from error

    result = subprocess.run(
        [str(python), "-m", "playwright", "install", "--dry-run", "chromium"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "Playwright could not determine the Chromium installation path. "
            f"{result.stderr.strip()}"
        )

    match = re.search(r"^\s*Install location:\s*(.+?)\s*$", result.stdout, re.MULTILINE)
    if not match:
        raise RuntimeError("Playwright did not report a Chromium installation path.")

    install_location = Path(match.group(1).strip())
    executable_candidates = (
        install_location / "chrome-win64" / "chrome.exe",
        install_location / "chrome-linux" / "chrome",
        install_location / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
    )
    executable = next((candidate for candidate in executable_candidates if candidate.is_file()), None)
    if executable is None:
        raise RuntimeError(
            "Playwright is installed but Chromium is unavailable. "
            "Run setup_environment.py again so the browser can be provisioned."
        )
    print(f"Chromium executable: {executable}")


def install() -> int:
    """Install Python requirements, Chromium, and validate the resulting environment."""

    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.", file=sys.stderr)
        return 1
    if not REQUIREMENTS_FILE.is_file():
        print(f"Missing dependency file: {REQUIREMENTS_FILE}", file=sys.stderr)
        return 1

    try:
        python = ensure_virtual_environment()
        run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(python), "-m", "pip", "install", "--upgrade", "-r", str(REQUIREMENTS_FILE)])
        run([str(python), "-m", "playwright", "install", "chromium"])
        verify_playwright(python)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        return 1

    print("Setup complete. Start the bot with run.cmd or run.ps1.")
    return 0


def check() -> int:
    """Validate the existing venv without installing or changing anything."""

    python = venv_python()
    if not python.is_file():
        print(f"Missing virtual environment interpreter: {python}", file=sys.stderr)
        return 1
    try:
        verify_playwright(python)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Environment check failed: {error}", file=sys.stderr)
        return 1
    print("Environment check passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the existing .venv and Chromium without installing anything",
    )
    args = parser.parse_args()
    return check() if args.check else install()


if __name__ == "__main__":
    raise SystemExit(main())
