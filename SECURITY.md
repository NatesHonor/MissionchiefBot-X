# Security policy

## Supported versions

Security fixes are applied to the latest release and the `main` branch. Older releases may not receive fixes; users should upgrade before reporting a problem.

## Reporting a vulnerability

Please use GitHub's **Report a vulnerability** feature under the repository Security tab. Do not disclose credentials, session cookies, account details, private mission data, or exploit details in a public issue.

Include the affected version, operating system, reproduction steps, impact, and any suggested mitigation. Maintainers will acknowledge a report when available, investigate it, and coordinate disclosure after a fix is ready.

## Security boundaries

Mission Helper runs locally and uses the credentials supplied by the operator to sign in to the selected MissionChief regional service. Credentials may be read from `config.ini` or `MISSIONCHIEF_*` environment variables. They are not intended to be committed, included in images, or sent to this project's maintainers.

The WebUI is designed for local use. Keep its host set to `127.0.0.1`; it has no authentication and must not be exposed directly to a network or the public internet.

Runtime logs can contain operational details. Review and redact logs before sharing them. Never share `config.ini`, `.env`, browser profiles, cookies, tokens, or screenshots containing private account information.

This project does not attempt to bypass access controls, rate limits, or service restrictions. See the legal and terms notice in the README before use.
