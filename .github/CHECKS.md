# Repository checks

GitHub Actions validates every pull request before it is merged. Workflows use
least-privilege permissions and `pull_request_target` jobs never check out or run
code from an untrusted pull request.

## Pull request policy

- **Validate PR description** requires meaningful Summary and Testing sections.
- **Lint PR title** enforces Conventional Commit-style pull request titles.
- **Apply conventional-type label** keeps one `type: ...` label in sync with the title.
- **Check PR artifacts** rejects secrets, runtime config, logs, bytecode, archives, and build output.

Example pull request titles:

- `feat(dispatch): add regional vehicle aliases`
- `fix(auth): handle expired browser sessions`
- `docs: clarify Docker configuration`

## CI and security

- **Quality and security** runs Ruff formatting/correctness checks, mypy, and Bandit.
- **Test and build** compiles, imports, and tests the application on Ubuntu and Windows.
- **Dependency review** blocks newly introduced high-severity vulnerable dependencies.
- **Python dependency audit** scans the full Python dependency set with `pip-audit`.
- **Secret scan** scans Git history with Gitleaks and the repository allowlist.
- **CodeQL** performs extended Python security analysis.
- **GitHub Actions lint** validates workflow syntax and expressions with actionlint.

## Docker

Docker-affecting pull requests build an `amd64` image without publishing it. Trusted
pushes to `main` and version tags build `amd64` and `arm64` images, publish immutable
digests to GHCR, and merge them into a multi-architecture manifest. Published builds
also include provenance and an SBOM.

## Re-running checks

Push a new commit, use GitHub's **Re-run jobs** button, dispatch a workflow manually,
or have a repository owner/member comment `/recheck` on the pull request.

## Recommended branch protection

In **Settings > Branches > Branch protection rules**, require these stable checks:

- `PR / Validate PR description`
- `PR / Lint PR title (conventional)`
- `PR Artifacts / Check PR artifacts`
- `CI / CI success`
- `Security / Dependency review`
- `Security / Secret scan`
- `Security / CodeQL (Python)`

Also enable required approving reviews, dismissal of stale approvals, resolution of
review conversations, and the repository setting that prevents force pushes to `main`.
