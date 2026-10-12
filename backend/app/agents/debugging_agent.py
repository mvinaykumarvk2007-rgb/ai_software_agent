from datetime import datetime, timezone

from app.schemas import DebugFinding, DebuggingReport, TestReport
from app.services.project_storage import get_project_manifest
from app.agents.testing_agent import (
    ReportNotFoundError,
    get_latest_test_report,
    run_project_tests,
)


def _recommended_action(category: str, message: str, details: str | None) -> str:
    evidence = f"{message} {details or ''}".lower()
    if category == "syntax":
        return "Correct the syntax error in the named file, then rerun project verification."
    if category == "dependency":
        return "Check the package name and version in the relevant dependency manifest, then reinstall dependencies."
    if category == "security":
        return "Review the reported unsafe pattern and replace it with a safe implementation before deployment."
    if category == "runtime":
        return "Reproduce the runtime failure using the reported output, fix the failing entry point, and rerun tests."
    if category == "build":
        return "Resolve the build error shown in the details and rerun the frontend or backend build."
    if "missing" in evidence or "not found" in evidence:
        return "Add the required file or correct the path/configuration referenced by this check."
    return "Review the check details, address the reported project structure issue, and rerun verification."


def debug_project(project_id: str) -> DebuggingReport:
    manifest = get_project_manifest(project_id)
    try:
        report = get_latest_test_report(project_id)
    except ReportNotFoundError:
        report = run_project_tests(project_id)
    findings = [
        DebugFinding(
            check_name=check.name,
            category=check.category,
            priority=(
                "high"
                if check.category in {"syntax", "security", "runtime", "build"}
                else "medium"
            ),
            summary=check.message,
            evidence=check.details or check.message,
            recommended_action=_recommended_action(
                check.category, check.message, check.details
            ),
        )
        for check in report.checks
        if check.status == "failed"
    ]
    blocked = sum(check.status == "blocked" for check in report.checks)
    if findings:
        summary = (
            f"Found {len(findings)} failed verification check(s). "
            "Review the findings and rerun tests after making fixes."
        )
    elif blocked:
        summary = (
            "No failing checks were found, but some runtime checks were blocked by "
            "the environment. Start Docker and rerun verification for full coverage."
        )
    else:
        summary = "No failing verification checks were found."

    return DebuggingReport(
        project_id=project_id,
        project_name=manifest.project_name,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        status="issues_found" if findings else "clean",
        summary=summary,
        findings=findings,
        test_report=report,
    )
