from datetime import datetime, timezone
import zipfile

from app.agents import debugging_agent, documentation_agent
from app.api import routes
from app.main import app
from app.schemas import (
    DebuggingReport,
    DocumentationResult,
    ProjectManifest,
    TestCaseResult as ProjectCheckResult,
    TestReport as ProjectTestReport,
    TestReportSummary as ProjectTestReportSummary,
)
from app.services import project_storage
from fastapi.testclient import TestClient

client = TestClient(app)


def make_test_report(status="passed", category="syntax"):
    checks = [
        ProjectCheckResult(
            name="Python syntax",
            category=category,
            status=status,
            duration_ms=1,
            message="Syntax is invalid" if status == "failed" else "Syntax is valid",
            details="backend/main.py: unexpected token" if status == "failed" else None,
        )
    ]
    failed = int(status == "failed")
    return ProjectTestReport(
        project_id="project-agent-test",
        project_name="Agent Test",
        target_stack="React + Python FastAPI + SQLite",
        tested_at=datetime.now(timezone.utc).isoformat(),
        total_checks=1,
        passed_count=int(status == "passed"),
        failed_count=failed,
        skipped_count=0,
        blocked_count=0,
        overall_status=status,
        summary=ProjectTestReportSummary(
            passed=int(status == "passed"),
            failed=failed,
            skipped=0,
            blocked=0,
            total=1,
            overall_status=status,
        ),
        checks=checks,
    )


def test_debug_agent_returns_targeted_findings(monkeypatch):
    manifest = ProjectManifest(
        project_id="project-agent-test",
        project_name="Agent Test",
        target_stack="React + Python FastAPI + SQLite",
        created_at="2026-01-01T00:00:00+00:00",
        files_count=1,
        total_bytes=10,
        file_paths=["backend/main.py"],
        generation_summary="Test project",
    )
    monkeypatch.setattr(debugging_agent, "get_project_manifest", lambda _pid: manifest)
    monkeypatch.setattr(
        debugging_agent, "get_latest_test_report", lambda _pid: make_test_report("failed")
    )

    result = debugging_agent.debug_project("project-agent-test")

    assert result.status == "issues_found"
    assert result.findings[0].priority == "high"
    assert "backend/main.py" in result.findings[0].evidence
    assert "rerun" in result.findings[0].recommended_action.lower()


def test_debug_agent_reports_clean_checks(monkeypatch):
    manifest = ProjectManifest(
        project_id="project-agent-test",
        project_name="Agent Test",
        target_stack="React + Python FastAPI + SQLite",
        created_at="2026-01-01T00:00:00+00:00",
        files_count=1,
        total_bytes=10,
        file_paths=["backend/main.py"],
        generation_summary="Test project",
    )
    monkeypatch.setattr(debugging_agent, "get_project_manifest", lambda _pid: manifest)
    monkeypatch.setattr(
        debugging_agent, "get_latest_test_report", lambda _pid: make_test_report()
    )

    result = debugging_agent.debug_project("project-agent-test")

    assert result.status == "clean"
    assert result.findings == []


def test_debug_agent_runs_tests_when_no_report_exists(monkeypatch):
    manifest = ProjectManifest(
        project_id="project-agent-test",
        project_name="Agent Test",
        target_stack="React + Python FastAPI + SQLite",
        created_at="2026-01-01T00:00:00+00:00",
        files_count=1,
        total_bytes=10,
        file_paths=["backend/main.py"],
        generation_summary="Test project",
    )
    monkeypatch.setattr(debugging_agent, "get_project_manifest", lambda _pid: manifest)

    def no_saved_report(_project_id):
        raise debugging_agent.ReportNotFoundError("No report found")

    monkeypatch.setattr(debugging_agent, "get_latest_test_report", no_saved_report)
    monkeypatch.setattr(debugging_agent, "run_project_tests", lambda _pid: make_test_report())

    result = debugging_agent.debug_project("project-agent-test")

    assert result.status == "clean"
    assert result.test_report.project_id == "project-agent-test"


def test_documentation_agent_persists_guide_and_updates_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(project_storage, "STORAGE_BASE_DIR", tmp_path)
    project_storage.save_generated_project(
        project_name="Agent Test",
        target_stack="React + Python FastAPI + SQLite",
        generation_summary="An example project.",
        files=[],
        project_id="project-agent-test",
    )

    result = documentation_agent.generate_project_documentation("project-agent-test")
    manifest = project_storage.get_project_manifest("project-agent-test")
    content, _ = project_storage.get_project_file_content(
        "project-agent-test", result.file_path
    )

    assert result.file_path == "docs/PROJECT_GUIDE.md"
    assert "Agent Test" in content
    assert "uvicorn main:app" in content
    assert result.file_path in manifest.file_paths
    assert manifest.files_count == 1
    with zipfile.ZipFile(project_storage.create_project_zip_buffer("project-agent-test")) as archive:
        assert result.file_path in archive.namelist()


def test_debug_and_documentation_endpoints(monkeypatch):
    report = make_test_report()
    manifest = ProjectManifest(
        project_id="project-agent-test",
        project_name="Agent Test",
        target_stack="React + Python FastAPI + SQLite",
        created_at="2026-01-01T00:00:00+00:00",
        files_count=1,
        total_bytes=10,
        file_paths=["docs/PROJECT_GUIDE.md"],
        generation_summary="Test project",
    )
    debug_result = DebuggingReport(
        project_id=report.project_id,
        project_name=report.project_name,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        status="clean",
        summary="No failing checks were found.",
        test_report=report,
    )
    documentation_result = DocumentationResult(
        project_id=manifest.project_id,
        project_name=manifest.project_name,
        file_path="docs/PROJECT_GUIDE.md",
        content="# Agent Test",
        manifest=manifest,
    )
    monkeypatch.setattr(routes, "debug_project", lambda _project_id: debug_result)
    monkeypatch.setattr(
        routes, "generate_project_documentation", lambda _project_id: documentation_result
    )

    debug_response = client.post("/api/projects/project-agent-test/debug")
    docs_response = client.post("/api/projects/project-agent-test/documentation")

    assert debug_response.status_code == 200
    assert debug_response.json()["status"] == "clean"
    assert docs_response.status_code == 200
    assert docs_response.json()["file_path"] == "docs/PROJECT_GUIDE.md"
