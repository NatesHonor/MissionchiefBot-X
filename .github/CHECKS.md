# CI Checks

This repository uses GitHub Actions for continuous integration. Here's what runs on every pull request:

## Checks

- **compatibility** - Python version, dependencies, Playwright setup, imports
- **lint (ruff)** - Code style and formatting
- **type-check (mypy)** - Type annotations
- **security (bandit)** - Security scanning
- **test (release notifications)** - Checks the release bot's PR comment logic
- **dependency-check** - Outdated dependency detection
- **CodeQL** - GitHub's built-in security analysis

## CI Results comment

After each PR workflow finishes, the **PR Check Summary** workflow (`.github/workflows/pr-check-summary.yml`) updates one **CI Results** comment on the pull request. The comment covers:

- **Every check** on the PR's latest commit, from every workflow (CI, PR, PR Artifacts, Security, Semantic PR Title, release-contract, Docker) plus CodeQL. It is not limited to the CI jobs. If a check was re-run, only its newest result counts.
- **Why checks failed**: for each failed check, the step that failed, the error annotations, the error lines from the job log, and how to fix that kind of failure.

The comment fills in as checks finish, and a newer push replaces the results. The workflow runs from the default branch and never runs code from the pull request.

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
