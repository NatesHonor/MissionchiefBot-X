from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    job: str
    why: str
    fix: str


CHECKS = (
    Check("Ruff lint", "quality", "Python correctness or maintainability rules failed.", "Run `python -m ruff check . --fix`, then resolve remaining findings."),
    Check("Ruff formatting", "quality", "Python formatting differs from the repository standard.", "Run `python -m ruff format .` and commit the result."),
    Check("Mypy typing", "quality", "Application types are inconsistent or incomplete.", "Run the mypy command from CONTRIBUTING.md and fix the first reported source error."),
    Check("Bandit security", "quality", "Static analysis found a medium-or-higher confidence security risk.", "Review the Bandit finding; remove unsafe behavior or add a narrowly justified exclusion."),
    Check("Python 3.11 / Linux", "ubuntu-py311", "The PR does not compile, import, or test successfully on the baseline Linux runtime.", "Reproduce with Python 3.11 on Linux and fix the first compile/import/test failure."),
    Check("Python 3.14 / Linux", "ubuntu-py314", "The PR is incompatible with the current Linux runtime.", "Reproduce with Python 3.14; update incompatible syntax or dependencies."),
    Check("Python 3.11 / Windows", "windows-py311", "The PR breaks baseline Windows compatibility.", "Reproduce with Python 3.11 on Windows; check paths, subprocess calls, and line endings."),
    Check("Python 3.14 / Windows", "windows-py314", "The PR breaks the current Windows runtime.", "Reproduce with Python 3.14 on Windows; update incompatible code or dependencies."),
    Check("Dependency review", "dependency-review", "A changed dependency introduces an unacceptable known vulnerability.", "Upgrade, replace, or remove the flagged dependency."),
    Check("Dependency audit", "dependency-audit", "The resolved Python dependency set contains a known vulnerability.", "Use the fixed version reported by pip-audit and update the dependency pin."),
    Check("Secret scan", "secret-scan", "The PR or repository history appears to contain a credential or secret.", "Revoke the credential, remove it from the change/history, and use repository secrets."),
    Check("CodeQL", "codeql", "CodeQL found a potential security or data-flow vulnerability.", "Open the CodeQL alert, trace the reported flow, and validate or sanitize the input."),
    Check("Workflow lint", "workflow-lint", "A GitHub Actions workflow has invalid syntax or unsafe expressions.", "Run actionlint and correct the exact workflow line reported."),
    Check("PR artifact hygiene", "check-pr-artifacts", "The PR includes generated, runtime, binary, or sensitive artifacts.", "Remove the listed files and add an appropriate `.gitignore` rule if needed."),
    Check("Docker compatibility", "validate", "The application cannot be built as the supported Linux container image.", "Run `docker build -t missionchiefbotx:test .` and fix the first failing build layer."),
)


def conclusion(check_runs: list[dict], job: str) -> tuple[str, str]:
    matches = [item for item in check_runs if item.get("name") == job]
    if not matches:
        return "pending", "This check has not reported a result for the current commit yet."
    value = matches[-1].get("conclusion") or "pending"
    if value in {"success", "neutral", "skipped"}:
        return "pass", "The check completed successfully." if value == "success" else f"The check was {value}."
    if value in {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}:
        return "fail", f"GitHub reported `{value}`. Open the linked job logs for the first concrete error."
    return "pending", f"The check is currently `{value}`."


def main() -> None:
    payload = json.loads(Path(os.environ["CHECK_RUNS_FILE"]).read_text(encoding="utf-8"))
    runs = payload.get("check_runs", [])
    passed = failed = pending = 0
    rows = []
    for number, item in enumerate(CHECKS, 1):
        status, detail = conclusion(runs, item.job)
        if status == "pass":
            passed += 1
            icon = "✅"
            guidance = "No action required."
        elif status == "fail":
            failed += 1
            icon = "❌"
            guidance = item.fix
        else:
            pending += 1
            icon = "⏳"
            guidance = "Wait for this check to complete; rerun the workflow if it never starts."
        rows.append(f"| {number} | {icon} {item.name} | {detail if status != 'fail' else item.why + ' ' + detail} | {guidance} |")

    completed = passed + failed
    compatibility = round((passed / completed) * 100) if completed else 0
    readiness = round((passed / len(CHECKS)) * 100)
    verdict = "Ready to merge" if failed == 0 and pending == 0 else "Needs attention" if failed else "Checks still running"
    report = [
        "# Pull Request Readiness Assessment",
        "",
        f"## {verdict}: **{readiness}%** overall readiness",
        "",
        f"- **Passed:** {passed}/{len(CHECKS)}",
        f"- **Failed:** {failed}/{len(CHECKS)}",
        f"- **Pending:** {pending}/{len(CHECKS)}",
        f"- **Measured compatibility:** {compatibility}% of completed checks",
        "",
        "> The score uses simple assumptions: every check has equal weight; successful, neutral, or intentionally skipped jobs pass; incomplete jobs remain pending; and failed jobs reduce compatibility. The linked job log is the source of truth for the exact error.",
        "",
        "| # | Check | Result and likely cause | Recommended fix |",
        "|---:|---|---|---|",
        *rows,
        "",
        "## Compatibility interpretation",
        "",
        "- **100%:** all quality, security, operating-system, Python-version, dependency, artifact, and container checks passed.",
        "- **80–99%:** broadly compatible, but the failed rows must be reviewed before merge.",
        "- **60–79%:** partial compatibility; expect failures for some users or deployment methods.",
        "- **Below 60%:** not considered compatible with the supported project matrix.",
    ]
    Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
