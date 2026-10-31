# MissionAutoReleaseBot

Install the GitHub App **MissionAutoReleaseBot** on this repository. Configure its App ID and private key as repository Actions secrets `RELEASE_BOT_APP_ID` and `RELEASE_BOT_PRIVATE_KEY`. Do not commit the key or print the installation token.

Required **repository** permissions for the app:

- Contents: **Read and write** — Release Please updates the release branch, tags and publishes releases.
- Pull requests: **Read and write** — Release Please creates/updates release PRs; the notifier reads merged PRs.
- Issues: **Read and write** — Release Please labels/issues and the notifier creates/updates PR conversation comments (GitHub's issues API).
- Metadata: **Read** (automatically granted).

The workflow's `GITHUB_TOKEN` only needs `contents: read` for checkout. Its installation token is scoped to this repository and the three requested permissions. The version manifest and versioning strategy are unchanged.

On pushes to `main` or manual dispatch, the existing Release Please workflow creates/updates the pending release PR first. Then the notifier reads the **actual version from the release PR's manifest diff** and reads the added changelog section for that version. It comments only on merged PRs targeting the default branch whose GitHub merge/squash commit SHA and PR number both occur in a newly added release-note entry. References without a matching merge commit are ignored; rebase/no-SHA entries are deliberately skipped rather than guessed. If Release Please has not produced a complete changelog diff, no comment is posted. The marker and App identity let subsequent runs update the same comment after version or release-PR changes instead of duplicating it. API failures are warnings, not a release blocker. The notification script and its tests are checked out from the trusted default branch; never run code checked out from an untrusted PR with this token.

Release notes now list every Conventional Commit type (`feat`, `fix`, `perf`, `revert`, `security`, `refactor`, `docs`, `test`, `build`, `ci`, `style`, `chore`) via `changelog-sections` in `release-please-config.json`. Only `feat`, `fix` and breaking changes still decide the version bump.

The notifier runs after every Release Please run, not only when the release PR is created. When a release is published, or when you run the workflow manually with **backfill** checked, it also goes through every published release and comments **Released! … included in vX.Y.Z** on each merged PR listed there. An existing "scheduled" comment is edited into the "released" one rather than duplicated. A PR listed in several releases gets the newest one. Only releases whose notes link both the PR and its merge commit are matched, which is the Release Please format; older hand-written release notes (v3.0.1, v3.0.2) have no such links, so their PRs are not commented on.

**Authors, credits and missed changes.** Release Please lists one line per squash-merged PR (its title) and skips commits it cannot parse. After every Release Please run, `.github/scripts/enrich-release-notes.cjs` updates the pending version's section in both the release PR body and `CHANGELOG.md` on the release branch. The GitHub release is created from the PR body, so the changes end up in the published release too.

- Every entry ends with the PR author's `@username`, or the commit author's for a commit pushed straight to `main`. For example: `* stop mission worker crashes (#95) (ad5fb7f) @NatesHonor`.
- If the PR description has a **Credits** section, those names are added after the author: `@NatesHonor (credit: Bob from Discord)`. Use this to credit people without a GitHub account. Write one name per line under a `## Credits` heading, or a single line such as `Credits: Bob, Alice`. HTML comments and `None` are ignored.
- **Other Changes** lists commits on `main` since the last published release that the generated notes don't link, in the same format. Examples: a merged PR whose title wasn't a Conventional Commit, or a commit pushed straight to `main`.

Release commits (`chore: release ...`) and merge commits are left out. Running again replaces the attribution and the Other Changes block instead of adding them twice. If the version section can't be found, nothing is changed.

**Credits.** Each merged PR that qualifies for a release credits its author (bots such as Dependabot are skipped):

- On the pending release PR, the bot keeps one **Credits** comment, e.g. `Thanks to @user for #75, #79`, and edits it as more PRs land. It's a comment rather than part of the PR body because Release Please rewrites the body on every run.
- When a release is published (or on a backfill run), the bot appends a **Credits** section to the GitHub release notes. The section is replaced on later runs, never duplicated, and the notes above it are not touched.

App-created release PRs can trigger normal pull-request checks; this workflow runs only for pushes to `main` and manual dispatch, not for changes to its own release PR. GitHub's policy checks for release PR titles may still need an explicit exemption for Release Please's `chore(main): release ...` titles; this change does not alter those unrelated policies.
