# MissionAutoReleaseBot

Install the GitHub App **MissionAutoReleaseBot** on this repository. Configure its App ID and private key as repository Actions secrets `RELEASE_BOT_APP_ID` and `RELEASE_BOT_PRIVATE_KEY`. Do not commit the key or print the installation token.

Required **repository** permissions for the app:

- Contents: **Read and write** — Release Please updates the release branch, tags and publishes releases.
- Pull requests: **Read and write** — Release Please creates/updates release PRs; the notifier reads merged PRs.
- Issues: **Read and write** — Release Please labels/issues and the notifier creates/updates PR conversation comments (GitHub's issues API).
- Metadata: **Read** (automatically granted).

The workflow's `GITHUB_TOKEN` only needs `contents: read` for checkout. Its installation token is scoped to this repository and the three requested permissions. The existing Release Please config and manifest are unchanged.

On pushes to `main` or manual dispatch, the existing Release Please workflow creates/updates the pending release PR first. Then the notifier reads the **actual version from the release PR's manifest diff** and reads the added changelog section for that version. It comments only on merged PRs targeting the default branch whose GitHub merge/squash commit SHA and PR number both occur in a newly added release-note entry. References without a matching merge commit are ignored; rebase/no-SHA entries are deliberately skipped rather than guessed. If Release Please has not produced a complete changelog diff, no comment is posted. The marker and App identity let subsequent runs update the same comment after version or release-PR changes instead of duplicating it. API failures are warnings, not a release blocker. The notification script and its tests are checked out from the trusted default branch; never run code checked out from an untrusted PR with this token.

App-created release PRs can trigger normal pull-request checks; this workflow runs only for pushes to `main` and manual dispatch, not for changes to its own release PR. GitHub's policy checks for release PR titles may still need an explicit exemption for Release Please's `chore(main): release ...` titles; this change does not alter those unrelated policies.
