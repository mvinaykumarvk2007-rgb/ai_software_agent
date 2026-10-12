import io
import zipfile
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    RequirementAnalysisResult,
    DevelopmentPlanResult,
    ArchitectureOverview,
    FeatureSuggestion,
    CodeGenerationBatch,
    GeneratedFile,
)
from app.services.gemini_service import GeminiAPIError
from app.services import gemini_service

client = TestClient(app)


@pytest.fixture
def sample_requirement_analysis():
    return RequirementAnalysisResult(
        project_name="Task Tracker",
        project_objective="Create an intuitive task management application.",
        user_requirements=["Track daily tasks", "Store in SQLite"],
        functional_requirements=["Create, update, delete tasks"],
        non_functional_requirements=["Fast response time"],
        proposed_features=[
            FeatureSuggestion(name="CRUD", description="Task CRUD", source="user_specified")
        ],
        acceptance_criteria=["Tasks persist across restarts"],
        selected_technologies=["React", "Python", "SQLite"],
        analysis_disclaimer="Note: Requirements have not been tested."
    )


@pytest.fixture
def sample_development_plan():
    return DevelopmentPlanResult(
        project_name="Task Tracker",
        architecture=ArchitectureOverview(
            pattern="Modular REST SPA",
            description="React frontend with FastAPI backend.",
            frontend_responsibilities=["UI"],
            backend_responsibilities=["API"],
            database_design="tasks table"
        ),
        file_tree=["frontend/src/App.jsx", "backend/main.py"],
        dependencies=[],
        implementation_steps=[],
        testing_strategy=[],
        planning_disclaimer="Note: No code executed."
    )


def test_code_gen_missing_api_key(sample_requirement_analysis, sample_development_plan, monkeypatch, tmp_path):
    """Verify that code generation returns 400 when API key is missing."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr(gemini_service, "BACKEND_ENV_FILE", tmp_path / "missing.env")

    payload = {
        "project_name": "Task Tracker",
        "requirements": "Build a responsive task tracker with SQLite storage.",
        "selected_technologies": ["React", "Python", "SQLite"],
        "requirement_analysis": sample_requirement_analysis.model_dump(),
        "development_plan": sample_development_plan.model_dump()
    }
    response = client.post("/api/agents/code-generation", json=payload)
    assert response.status_code == 400
    assert "Gemini API key is not configured" in response.json()["detail"]


def test_code_gen_missing_plan_payload(sample_requirement_analysis):
    """Verify that requests missing development_plan fail validation with 422."""
    payload = {
        "project_name": "Task Tracker",
        "requirements": "Build a responsive task tracker with SQLite storage.",
        "selected_technologies": ["React", "Python", "SQLite"],
        "requirement_analysis": sample_requirement_analysis.model_dump()
        # development_plan missing
    }
    response = client.post("/api/agents/code-generation", json=payload)
    assert response.status_code == 422


def test_code_gen_success_fastapi_mocked(sample_requirement_analysis, sample_development_plan):
    """Verify end-to-end code generation for React + FastAPI + SQLite with mocked AI response."""
    mock_batch = CodeGenerationBatch(
        generation_summary="Full-stack Task Tracker application generated successfully.",
        files=[
            GeneratedFile(
                path="frontend/src/App.jsx",
                content="import React from 'react'; export default function App() { return <h1>Task Tracker</h1>; }",
                description="Root UI component"
            ),
            GeneratedFile(
                path="backend/main.py",
                content="from fastapi import FastAPI\napp = FastAPI()\n@app.get('/')\ndef home(): return {'message': 'ok'}",
                description="FastAPI entrypoint"
            ),
            GeneratedFile(
                path="README.md",
                content="# Task Tracker\n\nRun instructions here.",
                description="Project documentation"
            )
        ]
    )

    with patch("app.agents.code_agent.generate_structured", return_value=mock_batch):
        payload = {
            "project_name": "Task Tracker",
            "requirements": "Build a responsive task tracker with SQLite storage.",
            "selected_technologies": ["React", "Python", "SQLite"],
            "requirement_analysis": sample_requirement_analysis.model_dump(),
            "development_plan": sample_development_plan.model_dump()
        }

        response = client.post("/api/agents/code-generation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        pid = data["project_id"]
        assert data["manifest"]["target_stack"] == "React + Python FastAPI + SQLite"
        assert data["manifest"]["files_count"] == 3
        assert "frontend/src/App.jsx" in data["manifest"]["file_paths"]
        assert "not been automatically executed" in data["manifest"]["generation_disclaimer"]

        # Test listing files
        files_resp = client.get(f"/api/projects/{pid}/files")
        assert files_resp.status_code == 200
        files_data = files_resp.json()
        assert len(files_data["files"]) == 3

        # Test reading file content
        content_resp = client.get(f"/api/projects/{pid}/files/frontend/src/App.jsx")
        assert content_resp.status_code == 200
        assert "Task Tracker" in content_resp.json()["content"]

        # Test downloading project ZIP
        download_resp = client.get(f"/api/projects/{pid}/download")
        assert download_resp.status_code == 200
        assert download_resp.headers["content-type"] == "application/zip"

        # Verify ZIP contains the files
        zip_bytes = io.BytesIO(download_resp.content)
        with zipfile.ZipFile(zip_bytes, "r") as z:
            names = z.namelist()
            assert "frontend/src/App.jsx" in names
            assert "backend/main.py" in names
            assert "manifest.json" in names


def test_code_gen_success_express_mocked(sample_requirement_analysis, sample_development_plan):
    """Verify target stack selection for Node.js Express + SQLite."""
    mock_batch = CodeGenerationBatch(
        generation_summary="Express + React app generated.",
        files=[
            GeneratedFile(
                path="backend/server.js",
                content="const express = require('express'); const app = express(); app.listen(5000);",
                description="Express server"
            ),
            GeneratedFile(
                path="frontend/src/App.jsx",
                content="export default function App() { return <div>Node App</div>; }",
                description="Frontend component"
            )
        ]
    )

    with patch("app.agents.code_agent.generate_structured", return_value=mock_batch):
        payload = {
            "project_name": "Node Task App",
            "requirements": "Build an Express and SQLite fullstack app.",
            "selected_technologies": ["React", "Node.js", "SQLite"],
            "requirement_analysis": sample_requirement_analysis.model_dump(),
            "development_plan": sample_development_plan.model_dump()
        }

        response = client.post("/api/agents/code-generation", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["manifest"]["target_stack"] == "React + Node.js Express + SQLite"


def test_unsafe_paths_rejected():
    """Verify that path traversal and absolute paths are rejected by GeneratedFile schema."""
    with pytest.raises(ValueError, match="Directory traversal"):
        GeneratedFile(path="../../etc/passwd", content="evil")

    with pytest.raises(ValueError, match="Absolute path"):
        GeneratedFile(path="/var/www/index.html", content="evil")

    with pytest.raises(ValueError, match="Drive letter"):
        GeneratedFile(path="C:/app/index.js", content="evil")


def test_duplicate_file_paths_rejected():
    """Verify that duplicate file paths in batch are rejected."""
    with pytest.raises(ValueError, match="Duplicate file path"):
        CodeGenerationBatch(
            generation_summary="duplicate test",
            files=[
                GeneratedFile(path="app.js", content="1"),
                GeneratedFile(path="app.js", content="2")
            ]
        )


def test_project_not_found():
    """Verify that querying a non-existent project returns 404."""
    response = client.get("/api/projects/non-existent-uuid/manifest")
    assert response.status_code == 404


def test_file_retrieval_path_traversal():
    """Verify that file retrieval rejects path traversal attempts."""
    response = client.get("/api/projects/some-id/files/../../secret.txt")
    assert response.status_code in (400, 404)
