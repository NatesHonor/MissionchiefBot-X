# Security Policy

## Report vulnerabilities privately

**Do not open a public issue, discussion, or pull request for a suspected vulnerability.** Public reports can expose users before a fix is available.

The preferred reporting method is a private GitHub security advisory:

1. Open the repository's **Security** tab.
2. Select **Advisories**.
3. Select **Report a vulnerability**.
4. Create and submit a draft advisory with the details below.

Direct link: https://github.com/NatesHonor/MissionchiefBot-X/security/advisories/new

GitHub keeps draft advisories private between the reporter and repository maintainers. They also provide a private workspace for discussing, developing, and crediting a coordinated fix.

If private vulnerability reporting is temporarily unavailable, contact the maintainer through the support link in the README and request a private security channel. Do not include exploit details, credentials, cookies, tokens, account data, or private logs in the initial message.

## What to include

- A clear description of the vulnerability and its impact
- The affected release, commit, operating system, and installation method
- Minimal reproduction steps or a proof of concept
- Relevant configuration with all secrets and personal data removed
- Whether exploitation requires local access, WebUI access, or a MissionChief account
- Suggested mitigations or fixes, if known
- Your preferred name and link for credit, or a request to remain anonymous

Never submit real passwords, API keys, session cookies, browser profiles, `.env` files, `config.ini`, unredacted logs, or personal account information. Use synthetic values in reproductions.

## Response and disclosure

Maintainers will aim to:

- acknowledge a report within 7 days;
- provide an initial assessment within 14 days;
- keep the reporter informed when meaningful progress occurs;
- coordinate a release and public disclosure after users have a reasonable opportunity to update.

These are targets rather than guarantees for a volunteer-maintained project. Please allow reasonable time for investigation and remediation before disclosure. Maintainers may close reports that are not reproducible, do not cross a security boundary, or only describe the documented risks of running third-party automation.

## Supported versions

Security fixes are provided for the latest published release and the `main` branch. Older releases may not receive backports. Reporters may be asked to confirm an issue against a currently supported version.

## Security boundaries

Mission Helper runs locally and signs in using credentials supplied by the operator. Credentials can be read from `config.ini` or `MISSIONCHIEF_*` environment variables and must never be committed, included in an image, attached to an issue, or sent to maintainers.

The WebUI is intended for loopback-only use. It has no authentication and must remain bound to `127.0.0.1`; exposing it to a LAN, proxy, container host interface, or the public internet is unsupported and unsafe.

Runtime logs and screenshots may contain operational or account details. Review and redact them before sharing. Never share browser storage, cookies, tokens, credentials, private mission data, or account identifiers.

This project does not support bypassing authentication, authorization, access controls, rate limits, or service restrictions. Reports should concern vulnerabilities in this repository, not requests to evade controls imposed by MissionChief or another service.

## Safe-harbor intent

Good-faith research that follows this policy, avoids privacy violations and service disruption, uses only accounts and systems the researcher is authorized to access, and gives maintainers reasonable time to respond will not be intentionally pursued by this project. This statement cannot authorize testing against MissionChief or any third-party system; their terms and policies still apply.
