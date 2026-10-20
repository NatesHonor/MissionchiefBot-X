# Repository instructions for AI agents

## Release-producing commit titles

This repository uses Release Please. Pull request titles and squash-merge commit titles **must use Conventional Commits** so merged work is included in automated versioning:

- `fix: ...` for bug fixes, documentation corrections, security hardening, CI repairs, dependency fixes, and other patch-level changes.
- `feat: ...` for backward-compatible features or significant new capabilities.
- `feat!: ...` or a `BREAKING CHANGE:` footer for incompatible changes requiring a major release.

Do not use non-release prefixes such as `security:`, `ci:`, `docs:`, `chore:`, or `refactor:` as the final PR/merge title when the change should trigger a release. Choose `fix:` or `feat:` based on user impact. Internal commits on a feature branch may be descriptive, but the PR title and final squash commit must be release-producing.

Before merging, verify the PR title follows this policy. Prefer squash merges so the validated PR title becomes the commit observed by Release Please.

## Pull requests

- Do not push directly to `main`.
- Run or inspect applicable checks before merging.
- Keep changes focused and explain their user impact.
- Never commit credentials, tokens, cookies, `.env`, or populated `config.ini` files.
