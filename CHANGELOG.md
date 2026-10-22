# Changelog

## [3.2.0](https://github.com/NatesHonor/MissionchiefBot-X/compare/v3.1.0...v3.2.0) (2026-10-22)


### Features

* **config:** migrate runtime configuration to environment ([1cee03d](https://github.com/NatesHonor/MissionchiefBot-X/commit/1cee03dc92e55d604ac271e603fe38e8428e1c1f))
* list all commit types in release notes and backfill release comments ([#81](https://github.com/NatesHonor/MissionchiefBot-X/issues/81)) ([1a2bfb6](https://github.com/NatesHonor/MissionchiefBot-X/commit/1a2bfb67424e69f415b1ec8e4a90f86fadf17093))
* migrate regional data to SQLite and streamline runtime ([#82](https://github.com/NatesHonor/MissionchiefBot-X/issues/82)) ([507dee9](https://github.com/NatesHonor/MissionchiefBot-X/commit/507dee94a870576aafa7ca680656c6fd00961b43))
* **release:** use MissionAutoReleaseBot and notify included PRs ([#80](https://github.com/NatesHonor/MissionchiefBot-X/issues/80)) ([a558d85](https://github.com/NatesHonor/MissionchiefBot-X/commit/a558d8580d78ea73a248d81129aa1395099334d8))


### Bug Fixes

* **ci:** align checks with environment migration ([394cfaf](https://github.com/NatesHonor/MissionchiefBot-X/commit/394cfaf91411f5a924211e1f08bfb5ffa343468b))
* restore release please and features removed in [#65](https://github.com/NatesHonor/MissionchiefBot-X/issues/65) ([#75](https://github.com/NatesHonor/MissionchiefBot-X/issues/75)) ([b4b2380](https://github.com/NatesHonor/MissionchiefBot-X/commit/b4b23805a184dbbf282f808b7ef395abc7494c45))
* update dependencies and read WebUI settings from .env in compose ([#79](https://github.com/NatesHonor/MissionchiefBot-X/issues/79)) ([e155a24](https://github.com/NatesHonor/MissionchiefBot-X/commit/e155a249fe8f077b8fc0d3d52b66371d31b66cd2))


### Build System

* **docker:** update Docker workflow actions and Playwright to latest versions ([#78](https://github.com/NatesHonor/MissionchiefBot-X/issues/78)) ([0c150b4](https://github.com/NatesHonor/MissionchiefBot-X/commit/0c150b47dcf82a7ccaf7a1ae0169da20f96fd6e3))

## [3.2.0](https://github.com/NatesHonor/MissionchiefBot-X/compare/v3.1.0...v3.2.0) (2026-10-21)


### Features

* **data:** store mission, vehicle, building, task, and region data in SQLite instead of JSON files, and add `manage_data.py` for managing the database ([#65](https://github.com/NatesHonor/MissionchiefBot-X/issues/65))
* **config:** move runtime configuration from `config.ini` to environment variables (`.env`) ([1cee03d](https://github.com/NatesHonor/MissionchiefBot-X/commit/1cee03dc92e55d604ac271e603fe38e8428e1c1f))


### Bug Fixes

* restore Release Please, the release workflows, `setup_environment.py`, the test suite, and the logging, WebUI and Docker work from #61–#64 that [#65](https://github.com/NatesHonor/MissionchiefBot-X/issues/65) removed ([#75](https://github.com/NatesHonor/MissionchiefBot-X/issues/75)) ([b4b2380](https://github.com/NatesHonor/MissionchiefBot-X/commit/b4b23805a184dbbf282f808b7ef395abc7494c45))
* **ci:** align checks with the environment variable migration ([394cfaf](https://github.com/NatesHonor/MissionchiefBot-X/commit/394cfaf91411f5a924211e1f08bfb5ffa343468b))


### Build System

* **docker:** update the Docker workflow actions to their latest versions and Playwright to 1.64.0 ([#78](https://github.com/NatesHonor/MissionchiefBot-X/issues/78)) ([0c150b4](https://github.com/NatesHonor/MissionchiefBot-X/commit/0c150b47dcf82a7ccaf7a1ae0169da20f96fd6e3))

## [3.1.0](https://github.com/NatesHonor/MissionchiefBot-X/compare/v3.0.2...v3.1.0) (2026-10-12)


### Features

* add semantic PR title validation ([2ad3968](https://github.com/NatesHonor/MissionchiefBot-X/commit/2ad3968d737d9515e08d5703b4c663d24698b730))
* enforce release-ready pull requests and notify Discord ([9fe520f](https://github.com/NatesHonor/MissionchiefBot-X/commit/9fe520f6a26322ce08a3d0c7161bc722706d6171))
* expose redesigned WebUI through Docker ([#64](https://github.com/NatesHonor/MissionchiefBot-X/issues/64)) ([290af94](https://github.com/NatesHonor/MissionchiefBot-X/commit/290af94045cc24e7f258fd4fec9c2d247948bddb))
* redesign console and file logging ([#61](https://github.com/NatesHonor/MissionchiefBot-X/issues/61)) ([4b3a0bf](https://github.com/NatesHonor/MissionchiefBot-X/commit/4b3a0bfb53796ece65aa1c5315f569fc8a13c6a1))


### Bug Fixes

* document release-producing commit requirements ([#59](https://github.com/NatesHonor/MissionchiefBot-X/issues/59)) ([9057a3e](https://github.com/NatesHonor/MissionchiefBot-X/commit/9057a3e41fda883e37570dd642f3d355bc35d463))
