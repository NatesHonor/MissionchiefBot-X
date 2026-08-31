# 🚨 Mission Helper

Mission Helper is an automation bot for [MissionChief](https://www.missionchief.com) designed to streamline gameplay and maximize efficiency.  
It handles everything from credit gathering to auto-dispatching, employee training, transport requests, and more — all while keeping resource usage low and performance high.

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
- `core.regions` owns region URLs and data paths.
- `core.auth`, `core.browser`, and `core.vehicle_state` own shared resources.
- `core.buildings`, `core.mission_*`, and `core.dispatching` contain the shared
  workflows.
- `regions/uk` and `regions/us` keep thin adapters for existing imports and
  region-specific vehicle mappings.

US, UK, and Germany are wired into the shared automation runtime. The remaining
region entries are URL metadata only until their localized vehicle rules and
selectors are implemented.

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
