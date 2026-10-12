import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import GeneratedFile
from app.services.project_storage import save_generated_project
from app.agents import testing_agent

client = TestClient(app)


@pytest.fixture
def valid_fastapi_project():
    """Creates a valid FastAPI full-stack project in storage."""
    files = [
        GeneratedFile(
            path="backend/main.py",
            content="from fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\ndef root(): return {'status': 'ok'}\n",
            description="Backend server"
        ),
        GeneratedFile(
            path="backend/database.py",
            content="import sqlite3\ndef get_db(): return sqlite3.connect('app.db')\n",
            description="Database module"
        ),
        GeneratedFile(
            path="frontend/package.json",
            content=json.dumps({
                "name": "test-frontend",
                "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
                "scripts": {"dev": "vite", "build": "vite build"}
            }),
            description="Frontend config"
        ),
        GeneratedFile(
            path="frontend/src/App.jsx",
            content="import React from 'react'; export default function App() { return <h1>Test</h1>; }",
            description="Root component"
        ),
        GeneratedFile(
            path=".env.example",
            content="DATABASE_URL=sqlite:///./app.db\nPORT=8000\n",
            description="Config template"
        ),
        GeneratedFile(
            path="README.md",
            content="# Test Project\n\nSetup instructions.",
            description="Docs"
        )
    ]
    pid, manifest = save_generated_project(
        project_name="Test Verifier",
        target_stack="React + Python FastAPI + SQLite",
        generation_summary="Testing fixture project",
        files=files
    )
    return pid


def test_testing_agent_valid_project(valid_fastapi_project):
    """Verify that a valid project passes structural, AST, and dependency checks."""
    pid = valid_fastapi_project
    response = client.post(f"/api/projects/{pid}/test")
    assert response.status_code == 200
    report = response.json()

    assert report["project_id"] == pid
    assert report["total_checks"] >= 5
    assert report["passed_count"] >= 4
    assert report["failed_count"] == 0
    assert report["blocked_count"] >= 1  # Docker container execution is blocked on host
    assert report["overall_status"] == "passed"

    check_names = [c["name"] for c in report["checks"]]
    assert "Manifest Integrity" in check_names
    assert "Python AST Syntax Validation" in check_names
    assert "JSON Syntax & Integrity" in check_names
    assert "Frontend Package Specification" in check_names
    assert "Containerized Runtime Isolation" in check_names

    # Verify report retrieval endpoint
    report_resp = client.get(f"/api/projects/{pid}/test-report")
    assert report_resp.status_code == 200
    assert report_resp.json()["project_id"] == pid


def test_testing_agent_alias_endpoint(valid_fastapi_project):
    """Verify POST /api/agents/testing alias endpoint works."""
    pid = valid_fastapi_project
    response = client.post("/api/agents/testing", json={"project_id": pid})
    assert response.status_code == 200
    assert response.json()["project_id"] == pid


def test_testing_agent_invalid_project_id():
    """Verify that a non-existent project returns 404."""
    response = client.post("/api/projects/unknown-uuid-123/test")
    assert response.status_code == 404


def test_testing_agent_path_traversal_rejected():
    """Verify that traversal in project ID is rejected."""
    response = client.post("/api/projects/..%2f..%2fetc/test")
    assert response.status_code in (400, 404)


def test_testing_agent_malformed_python_syntax():
    """Verify that invalid Python syntax triggers a failed AST check."""
    files = [
        GeneratedFile(
            path="backend/main.py",
            content="def broken_syntax(::: this is invalid syntax!!\n",
            description="Broken file"
        ),
        GeneratedFile(
            path="frontend/package.json",
            content=json.dumps({"dependencies": {"react": "18"}, "scripts": {"build": "vite"}}),
            description="Frontend config"
        ),
        GeneratedFile(path="README.md", content="# Test", description="Docs")
    ]
    pid, _ = save_generated_project(
        project_name="Broken Python",
        target_stack="React + Python FastAPI + SQLite",
        generation_summary="Broken syntax test",
        files=files
    )

    response = client.post(f"/api/projects/{pid}/test")
    assert response.status_code == 200
    report = response.json()

    assert report["failed_count"] >= 1
    assert report["overall_status"] == "failed"

    ast_check = next(c for c in report["checks"] if c["name"] == "Python AST Syntax Validation")
    assert ast_check["status"] == "failed"
    assert "backend/main.py" in ast_check["details"]


def test_testing_agent_malformed_json():
    """Verify that corrupted JSON triggers a failed JSON check."""
    files = [
        GeneratedFile(
            path="backend/main.py",
            content="print('ok')\n",
            description="Valid python"
        ),
        GeneratedFile(
            path="frontend/package.json",
            content="{ invalid_json: missing_quotes, }",
            description="Corrupt json"
        ),
        GeneratedFile(path="README.md", content="# Test", description="Docs")
    ]
    pid, _ = save_generated_project(
        project_name="Broken JSON",
        target_stack="React + Python FastAPI + SQLite",
        generation_summary="Corrupt json test",
        files=files
    )

    response = client.post(f"/api/projects/{pid}/test")
    assert response.status_code == 200
    report = response.json()

    assert report["failed_count"] >= 1
    assert report["overall_status"] == "failed"

    json_check = next(c for c in report["checks"] if c["name"] == "JSON Syntax & Integrity")
    assert json_check["status"] == "failed"


def test_testing_agent_missing_entrypoint():
    """Verify that missing entrypoints are caught."""
    files = [
        GeneratedFile(path="misc.txt", content="hello", description="Random file"),
        GeneratedFile(path="README.md", content="# Test", description="Docs")
    ]
    pid, _ = save_generated_project(
        project_name="Missing Entrypoint",
        target_stack="React + Python FastAPI + SQLite",
        generation_summary="Missing entrypoint test",
        files=files
    )

    response = client.post(f"/api/projects/{pid}/test")
    assert response.status_code == 200
    report = response.json()

    assert report["failed_count"] >= 1
    entry_check = next(c for c in report["checks"] if c["name"] == "Core Entrypoint Structure")
    assert entry_check["status"] == "failed"


def test_testing_agent_report_not_found():
    """Verify that requesting a report before running tests returns 404."""
    files = [GeneratedFile(path="README.md", content="# Empty", description="Docs")]
    pid, _ = save_generated_project(
        project_name="No Report Yet",
        target_stack="React + Python FastAPI + SQLite",
        generation_summary="No report",
        files=files
    )
    response = client.get(f"/api/projects/{pid}/test-report")
    assert response.status_code == 404


def test_testing_agent_never_executes_generated_frontend_build(monkeypatch):
    """Generated build scripts must not be executed on the host machine."""
    files = [
        GeneratedFile(path="backend/main.py", content="print('not run')", description="Backend"),
        GeneratedFile(
            path="frontend/package.json",
            content=json.dumps({
                "dependencies": {"react": "18"},
                "scripts": {"build": "node -e \"require('fs').writeFileSync('host.txt', 'unsafe')\""},
            }),
            description="Frontend config",
        ),
    ]
    project_id, _ = save_generated_project(
        project_name="Untrusted Build",
        target_stack="React + Python FastAPI + SQLite",
        generation_summary="Build safety regression test",
        files=files,
    )

    monkeypatch.setattr(testing_agent, "is_docker_available", lambda: (False, "Docker unavailable"))
    monkeypatch.setattr(testing_agent, "_is_tool_available", lambda _name: True)
    monkeypatch.setattr(
        testing_agent.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("Generated project code was executed."),
    )

    report = testing_agent.run_project_tests(project_id)
    build_check = next(check for check in report.checks if check.name == "Frontend Production Build")
    assert build_check.status == "blocked"
