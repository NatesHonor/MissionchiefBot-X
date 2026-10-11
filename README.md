# 🚨 Mission Helper

Mission Helper (MissionchiefBot-X) is an unofficial Python and Playwright automation application for MissionChief. It provides mission collection and dispatch, transport handling, employee training, recruiting, task collection, regional vehicle mapping, a local WebUI, and Docker support.

> [!WARNING]
> MissionChief's terms may prohibit automated gameplay. This project is independent and is not created, approved, sponsored, maintained, or supported by MissionChief, SHPlay GmbH, Xyrality GmbH, or their affiliates. Use it only after confirming that your intended use is permitted. You are responsible for your account, credentials, network activity, and compliance with applicable rules and laws. Do not use this project to bypass access controls or rate limits, exploit bugs, interfere with others, or continue after an operator asks you to stop.

The software is provided as-is. The maintainers are not responsible for account action, lost progress, downtime, service changes, data loss, or other consequences of its use. Review the applicable service's current terms and privacy policy before use.

## Features

- Mission collection, filtering, prioritization, and dispatch
- Distance-aware vehicle and personnel selection
- Transport and prisoner handling
- Optional training, recruiting, special-resource, and task workflows
- Shared runtime with localized data for supported regions
- Local control WebUI and headless operation
- Windows setup scripts and multi-architecture Docker images

## Compatibility

- **Python:** 3.11 and 3.14 are tested on Windows and Linux.
- **Operating systems:** Windows and Linux are tested in CI.
- **Containers:** `linux/amd64` and `linux/arm64` images are published.
- **Regions:** US, UK, Australia, Germany, the Netherlands, Sweden, Portugal, Denmark, Poland, and France.
- **Support:** fixes target the latest release and `main`.

## Install and run

### Windows

```powershell
git clone https://github.com/NatesHonor/MissionchiefBot-X.git
cd MissionchiefBot-X
copy config.ini.example config.ini
python setup_environment.py
./run.ps1
```

Edit `config.ini` before starting. `run.cmd` is also available. To validate an existing environment without changing it, run `python setup_environment.py --check`.

### Docker

Copy `.env.example` to `.env`, set `MISSIONCHIEF_USERNAME` and `MISSIONCHIEF_PASSWORD`, then run:

```bash
docker compose up --build
```

Published images are available at `ghcr.io/nateshonor/missionchiefbot-x`.

## Configuration

`core.settings` loads a validated configuration snapshot from `config.ini`. Docker and deployment environments can override settings with `MISSIONCHIEF_*` environment variables. Start from `config.ini.example`; never commit the resulting `config.ini` or `.env` file.

The WebUI is disabled by default. If enabled, keep it bound to `127.0.0.1`: it has no authentication and must not be exposed directly to a network or the public internet.

Mission collection includes alliance missions by default. Set `include_alliance_missions = false` under `[missions]`, or `MISSIONCHIEF_INCLUDE_ALLIANCE_MISSIONS=false`, to collect only your own missions.

Region-specific exclusions live in `regions/<region>/data/mission_ignore_list.json`:

```json
{
  "mission_ids": [],
  "mission_names": ["Mission name to skip"],
  "contains": ["airport"]
}
```

## Architecture

- `Main.py` loads settings, optionally starts the WebUI, and launches `core.runner.run_bot()`.
- `core.auth`, `core.browser`, and `core.vehicle_state` own shared runtime resources.
- `core.mission_*`, `core.buildings`, and `core.dispatching` implement collection and dispatch workflows.
- `core.regions` resolves regional URLs, localization, aliases, requirement maps, and data paths.
- `regions/<region>` contains thin compatibility entrypoints and localized data.
- `utils` contains transport, training, recruiting, task, and vehicle helpers.

Regional support is data-driven. A new region requires a real official hostname, verified localized mappings, a mission-ignore file, and passing mapping and runtime tests. Unknown regions are rejected rather than redirected elsewhere.

## Data, privacy, and security

The application runs locally and signs in with credentials supplied by its operator. The repository does not collect telemetry or send credentials to maintainers. Runtime logs may contain operational details; redact them before sharing. Never share configuration files, `.env` files, browser profiles, cookies, tokens, or account screenshots.

See [SECURITY.md](SECURITY.md) for vulnerability reporting and security boundaries.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, quality checks, and pull-request requirements. CI runs Ruff, mypy, Bandit, pytest on Windows and Linux, dependency auditing, secret scanning, CodeQL, workflow linting, and Docker validation.

## Downloads and support

Use versioned source archives from [GitHub Releases](https://github.com/NatesHonor/MissionchiefBot-X/releases) or the published container image. A separately hosted convenience download is available at [files.natemarcellus.com](https://files.natemarcellus.com/download/MissionchiefBot); verify its version against the corresponding GitHub release.

- [Support](https://support.natemarcellus.com)
- [Discord community](https://discord.gg/UrGZwfjxND)

MissionchiefBot-X is intended to remain free to download and use. Be cautious of anyone claiming to represent the project who requests payment or payment details.
