# Contributing

Thanks for helping improve Mission Helper.

## Before starting

- Search existing issues and pull requests before opening a duplicate.
- Keep changes focused and avoid committing credentials, logs, caches, generated files, or runtime data.
- For regional support, provide a real official hostname and verified localized vehicle and requirement data.
- Do not add behavior intended to bypass access controls, rate limits, or operator restrictions.

## Development setup

Python 3.11 is the primary CI version. From the repository root:

```bash
python -m venv .venv
# Windows: .venv\Scripts\python -m pip install -r requirements.txt ruff mypy bandit pytest pytest-asyncio
# Linux/macOS: .venv/bin/python -m pip install -r requirements.txt ruff mypy bandit pytest pytest-asyncio
python -m playwright install chromium
```

Install the Playwright browser separately after installing the Python dependencies.

## Required checks

Run these before submitting a pull request:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy core/ utils/ regions/ Main.py
# Run when a tests/ directory is present.
python -m pytest tests/
```

Changes to Docker files should also pass:

```bash
docker build -t missionchiefbotx:test .
```

## Pull requests

Use a Conventional Commit-style title, such as `fix(auth): handle expired sessions`. Complete the Summary and Testing sections in the pull request template. Add or update tests for behavioral changes and explain any check that could not be run.

By contributing, you agree that your contribution is provided under the repository's license and subject to the notices in the README.
