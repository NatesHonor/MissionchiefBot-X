# 🚨 Mission Helper

Mission Helper is an unofficial third-party automation application for [MissionChief](https://www.missionchief.com) designed to streamline gameplay and maximize efficiency.
It handles everything from credit gathering to auto-dispatching, employee training, transport requests, and more — all while keeping resource usage low and performance high.

---

## ⚠️ Important legal, terms, and safety notice

**Read this before installing, running, or distributing Mission Helper.**

Mission Helper / MissionchiefBotX is independent, unofficial software. It is not created,
owned, operated, approved, sponsored, endorsed, maintained, or supported by MissionChief,
SHPlay GmbH, Xyrality GmbH, any MissionChief regional operator, or any of their affiliates,
partners, licensors, competitors, or other third parties. MissionChief, SHPlay, Xyrality,
and related names, logos, and services belong to their respective owners. No relationship,
partnership, sponsorship, or endorsement should be inferred from this project.

The [official MissionChief terms and conditions](https://www.missionchief.com/agb) currently
state that tools, scripts, bots, and other programs suitable for automatically performing
activities in a game are prohibited, and that games must be used personally. Therefore,
**using this application may violate MissionChief's terms, game rules, or other policies.**
The existence of this repository, its API integrations, or a working release does not mean
that MissionChief has authorized it. The same warning applies to every supported regional
MissionChief service; check the rules for the specific service and region you use.

Use this software only if you have independently confirmed that your intended use is
permitted, preferably through current written authorization from the applicable operator.
If you cannot confirm that, do not run it. Rules and policies can change, so review the
official [terms and conditions](https://www.missionchief.com/agb), [privacy policy](https://www.missionchief.com/datenschutz),
and [imprint/operator information](https://www.missionchief.com/impressum) before each
major update or change in use. These links are provided for convenience and the official
operator's current documents control if anything here conflicts with them.

You are solely responsible for your account, credentials, devices, network activity, and
compliance with all applicable laws, terms, game rules, and third-party policies. Do not
use this project to evade restrictions, create or operate prohibited multiple accounts,
exploit bugs, bypass rate limits or access controls, overload a service, interfere with
other players, or continue after the operator asks you to stop. Keep credentials out of
issues, screenshots, logs, commits, and shared configuration files, and stop using the
application immediately if you suspect an account, security, or terms-of-service problem.

This project is provided for informational and experimental purposes **as-is**, without
any promise that it is permitted, safe, accurate, available, or compatible with any
MissionChief service. To the maximum extent permitted by applicable law, the maintainers
are not responsible for account suspension or termination, lost progress, lost virtual
items or currency, service changes, downtime, data loss, security incidents, or any other
loss resulting from use or inability to use this project. Nothing in this notice is legal
advice, creates a contract with MissionChief or its operator, or guarantees protection
from enforcement. Obtain advice from a qualified lawyer for your situation.

**Last reviewed:** 2026-08-30. Official policies may change after this date; always verify
the current policy directly with the applicable operator.

---

## 💙 Free forever

MissionchiefBotX is intended to remain free forever. The maintainers will never require
payment, a subscription, or a purchase to download, access, or use this project. Be
careful of anyone claiming to represent this project who asks you for money or payment
details.

---

## ✨ Features

- **Credit Gathering**: Automatically solves missions to maximize income.
- **Auto Dispatching**: Smart dispatch system with mission prioritization and geographic clustering.
- **Mission Gathering**: Collects and organizes missions for efficient handling.
- **Employee Training**: Automates staff training workflows.
- **Transport Requests**: Handles hospital and prison rerouting with adaptive transport logic.
- **Support & Auto Updating**: Built-in support hooks and seamless auto-update system.

## Project layout

The bot has one runtime and one set of mission/dispatch services. Region folders
only provide compatibility entrypoints and region data, so adding a new region
does not require copying the login, browser, parser, or dispatch loops.

- `Main.py` starts `core.runner.run_bot()`.
- `core.settings` loads one validated configuration snapshot and applies Docker
  environment overrides.
- `core.regions` owns region URLs, language catalogs, aliases, requirement maps,
  data paths, and region profiles.
- `core.auth`, `core.browser`, and `core.vehicle_state` own shared resources.
- `core.buildings`, `core.mission_*`, and `core.dispatching` contain the shared
  workflows.
- `regions/<region>.py` holds that region's vehicle substitutions;
  `regions/defaults/<region>/` holds the shipped alias and requirement mappings.

All bot data lives in SQLite (`data/missionchief.sqlite3`):

- **Defaults** (`regions/defaults/<region>/`): vehicle aliases, personnel
  aliases, requirement mappings and the mission ignore list. They are seeded
  into the database on startup and persist there. Your own edits are kept;
  a default is only refreshed when the shipped version changes.
- **Gathered data**: vehicle IDs, building IDs, active missions and the
  mission index. These are never shipped. If the database has none for your
  region yet, the bot gathers them from the game and stores them.

Use `python manage_data.py` to view, edit, export, or back up stored data.

US, UK, Australia, Germany, the Netherlands, Sweden, Portugal, Denmark, Poland,
and France are wired into the same automation runtime.

### Run locally on Windows

```powershell
python setup_environment.py
```

This creates `.venv`, installs the requirements and matching Playwright Chromium browser, and verifies the environment. Run the bot with `run.cmd` or `./run.ps1`.

## 🐳 Run with Docker

1. Copy `.env.example` to `.env` and set `MISSIONCHIEF_USERNAME` and `MISSIONCHIEF_PASSWORD`.
2. Run:

```bash
docker compose up --build
```

Published images are available as `ghcr.io/nateshonor/missionchiefbot-x`.

## Releasing

Release Please maintains one release pull request containing all releasable changes merged to `main` since the previous release. Pull request titles must use Conventional Commit prefixes so the correct version is selected:

- `fix:` creates a patch release.
- `feat:` creates a minor release.
- `feat!:` or a `BREAKING CHANGE:` footer creates a major release.

Merging the Release Please pull request creates the `vMAJOR.MINOR.PATCH` git tag and publishes the corresponding GitHub Release. Normal feature and fix pull requests do not publish a release directly. Squash merges are recommended so the PR's Conventional Commit title is preserved as the release-producing commit.

## 📥 Download

Download Mission Helper from [GitHub Releases](https://github.com/NatesHonor/MissionchiefBot-X/releases).

## 🆘 Support

Visit the [support page](https://support.natemarcellus.com) or join the [Discord community](https://discord.gg/UrGZwfjxND).
