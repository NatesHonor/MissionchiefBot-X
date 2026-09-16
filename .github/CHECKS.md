# CI Checks

This repository uses GitHub Actions for continuous integration. Here's what runs on every pull request:

## Checks

- **compatibility** - Python version, dependencies, Playwright setup, imports
- **lint (ruff)** - Code style and formatting
- **type-check (mypy)** - Type annotations
- **security (bandit)** - Security scanning
- **test (pytest)** - Unit tests
- **dependency-check** - Outdated dependency detection
- **CodeQL** - GitHub's built-in security analysis

## Re-running Checks

If you need to re-run the CI checks, you have several options:

### Option 1: Push to the branch
Simply push new commits to your PR branch and the checks will automatically re-run.

### Option 2: Use the /recheck command
Comment `/recheck` on the pull request to trigger a manual re-run.

### Option 3: GitHub Actions tab
Go to the [Actions tab](../../actions) and click "Re-run all jobs" on the latest workflow run.

### Option 4: Manual workflow dispatch
Use the "Manual CI Re-run" workflow from the Actions tab.
