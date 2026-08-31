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
  data paths, and standardized region entrypoints.
- `core.auth`, `core.browser`, and `core.vehicle_state` own shared resources.
- `core.buildings`, `core.mission_*`, and `core.dispatching` contain the shared
  workflows.
- `regions/uk` and `regions/us` keep thin adapters for existing imports and
  region-specific vehicle mappings.

US, UK, Australia, Germany, the Netherlands, Sweden, Portugal, and Denmark are wired into the
same automation runtime.  Each region keeps its own vehicle aliases, requirement
classification, localized labels, and cache directory, while browser/login/API,
mission parsing, dispatching, transport, and background loops remain shared.

The project does not invent a regional server for New Zealand.  A region must have a
real MissionChief service URL and a verified set of game vehicle names before it can be
enabled.  New Zealand remains explicitly unsupported until an official service is
identified; the launcher rejects it instead of silently using another country's site.

### Mission ignore list

To keep a mission type out of collection and dispatch, edit the region-specific file
`regions/<region>/data/mission_ignore_list.json`.  Use mission IDs for one-off active
missions, exact names for stable mission types, or `contains` for a name fragment:

```json
{
  "mission_ids": [],
  "mission_names": ["Mission name to skip"],
  "contains": ["airport"]
}
```

The list is read before detailed mission pages are scanned.  Mission names are matched
without accents or punctuation, and an empty or missing file disables filtering.

Mission collection includes alliance missions by default so existing configurations keep
their current behavior.  Set `include_alliance_missions = false` under `[missions]`, or
set `MISSIONCHIEF_INCLUDE_ALLIANCE_MISSIONS=false`, to collect and dispatch only your own
missions.  This setting controls the marker feed before the ignore-list rules are applied.

---

## 🐳 Run with Docker

The image includes Python, the project dependencies, and the Playwright Chromium browser.

1. Copy `.env.example` to `.env` and set `MISSIONCHIEF_USERNAME` and `MISSIONCHIEF_PASSWORD`.
2. Build and start the bot:

   ```bash
   docker compose up --build
   ```

The container runs headless by default, stores runtime logs in `./logs`, and builds the
`missionchiefbotx:latest` image. To build or run it directly:

```bash
docker build -t missionchiefbotx:latest .
docker run --rm --name missionchiefbotx --env-file .env -v "${PWD}/logs:/app/logs" missionchiefbotx:latest
```

The repository's `config.ini` is intentionally excluded from the image. Docker settings
can be supplied with the `MISSIONCHIEF_*` environment variables; a custom config can also
be mounted at `/app/config.ini` if needed.

GitHub Actions builds the image for pull requests and publishes it to GitHub Container
Registry for pushes to `main` and version tags. Published images are available as
`ghcr.io/nateshonor/missionchiefbot-x`.

---

## 📥 Download

To download Mission Helper, click [here](https://files.natemarcellus.com/download/MissionchiefBot).

---

## 🆘 Support

Need help? Visit our support page [here](https://support.natemarcellus.com).

---

## 💬 Community

Join our Discord server to connect with other players and get live updates:  
[Join Discord](https://discord.gg/UrGZwfjxND)

---

## 📜 Latest Changelog

### 🆕 Update (v3.0.1x) - Bot Remake

#### 🎉 New Features

**🔧 Bot**
- Improved performance and reliability  
- Added auto installation  
- Added logging  
- Better integration with Launcher  
- Fixed issues with credit gathering  
- Fixed issue with bot only using 1 thread  
- Added more customization  
- Decreased resource usage  
- Resource balancing to prevent over-dispatching  
- Smart transport handling with hospital/prison rerouting  
- Mission prioritization by severity  
- Geographic clustering of units to reduce travel time  
- Adaptive scaling of browser instances based on mission volume  
- API hook support for faster dispatch  
- Rate limiting safeguards for fair-use compliance  
- Auto Updating  

**🚀 Launcher**
- Fixed console output issues  
- Fixed launcher being unmovable  
- Fixed logging problems  
- Fixed launcher not stopping correctly  
- Simplified codebase for smaller footprint  
- Added auto-scroll toggle button  
- Configurable profiles for different play styles  
- Error recovery with automatic retry on failed dispatches  
- Auto Updating  

**🐞 Bug Fixes**
- Included in features above  

**📊 Logging & Analytics**
- Mission outcomes and dispatch times stored for later review  
- Transport durations tracked for optimization  
- Alliance vs. solo mission contributions logged  

---

## 🙌 Feedback

Your feedback is important! It helps us improve Mission Helper and make the game better for everyone.  
Please share your thoughts on our [support page](https://support.natemarcellus.com) or in the [Discord server](https://discord.gg/UrGZwfjxND).

---
