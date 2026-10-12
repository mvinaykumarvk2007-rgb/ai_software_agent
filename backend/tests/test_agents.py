import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    RequirementAnalysisResult,
    FeatureSuggestion,
    DevelopmentPlanResult,
    ArchitectureOverview,
    PlannedDependency,
    ImplementationStep,
)
from app.services import gemini_service
from app.services.gemini_service import (
    GeminiMissingKeyError,
    GeminiAPIError,
    get_model_name,
)

client = TestClient(app)


def test_empty_model_configuration_uses_default(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "   ")
    assert get_model_name() == "gemini-3.8-flash"


def test_api_key_is_read_from_backend_env_file_at_request_time(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=test-key-from-file\n", encoding="utf-8")
    monkeypatch.setattr(gemini_service, "BACKEND_ENV_FILE", env_file)
    monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_api_key_here")

    assert gemini_service.get_api_key() == "test-key-from-file"


def test_requirement_agent_missing_api_key(monkeypatch, tmp_path):
    """Verify that a missing or placeholder API key returns HTTP 400 without crashing."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr(gemini_service, "BACKEND_ENV_FILE", tmp_path / "missing.env")

    payload = {
        "project_name": "Task Tracker",
        "requirements": "Build a responsive task tracker with SQLite storage.",
        "selected_technologies": ["React", "Python", "SQLite"]
    }
    response = client.post("/api/agents/requirement-analysis", json=payload)
    assert response.status_code == 400
    assert "Gemini API key is not configured" in response.json()["detail"]


def test_requirement_agent_validation_error():
    """Verify that invalid inputs are rejected with 422 before touching the provider."""
    payload = {
        "project_name": "   ",
        "requirements": "Too short",
        "selected_technologies": []
    }
    response = client.post("/api/agents/requirement-analysis", json=payload)
    assert response.status_code == 422


def test_requirement_agent_success_mocked():
    """Verify end-to-end requirement analysis with mocked provider response."""
    mock_result = RequirementAnalysisResult(
        project_name="Task Tracker",
        project_objective="Create an intuitive task management application.",
        user_requirements=["Track daily tasks", "Store in SQLite"],
        functional_requirements=["Create, update, delete tasks", "Filter tasks by status"],
        non_functional_requirements=["Fast response time under 100ms", "Local data persistence"],
        proposed_features=[
            FeatureSuggestion(
                name="Task CRUD",
                description="Core task management operations",
                source="user_specified"
            ),
            FeatureSuggestion(
                name="Priority Labels",
                description="Color-coded task priorities",
                source="ai_suggested"
            )
        ],
        acceptance_criteria=["Tasks persist across restarts", "UI updates immediately"],
        selected_technologies=["React", "Python", "SQLite"],
        analysis_disclaimer="Note: Requirements and suggestions are generated for planning purposes and have not been tested or implemented."
    )

    with patch("app.agents.requirement_agent.generate_structured", return_value=mock_result):
        payload = {
            "project_name": "Task Tracker",
            "requirements": "Build a responsive task tracker with SQLite storage.",
            "selected_technologies": ["React", "Python", "SQLite"]
        }
        response = client.post("/api/agents/requirement-analysis", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["project_name"] == "Task Tracker"
        assert len(data["proposed_features"]) == 2
        assert data["proposed_features"][0]["source"] == "user_specified"
        assert data["proposed_features"][1]["source"] == "ai_suggested"
        assert "not been tested" in data["analysis_disclaimer"]


def test_requirement_agent_rate_limit_handled():
    """Verify that a 429 rate limit from Gemini is passed to client as HTTP 429."""
    with patch(
        "app.agents.requirement_agent.generate_structured",
        side_effect=GeminiAPIError("Rate limit exceeded. Please wait.", status_code=429)
    ):
        payload = {
            "project_name": "Task Tracker",
            "requirements": "Build a responsive task tracker with SQLite storage.",
            "selected_technologies": ["React", "Python", "SQLite"]
        }
        response = client.post("/api/agents/requirement-analysis", json=payload)
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]


def test_planning_agent_missing_api_key(monkeypatch, tmp_path):
    """Verify that missing API key returns 400 for planning agent."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr(gemini_service, "BACKEND_ENV_FILE", tmp_path / "missing.env")

    req_data = {
        "project_name": "Task Tracker",
        "project_objective": "Create an intuitive task management application.",
        "user_requirements": ["Track daily tasks"],
        "functional_requirements": ["Task CRUD"],
        "non_functional_requirements": ["Fast response"],
        "proposed_features": [
            {"name": "Task CRUD", "description": "Manage tasks", "source": "user_specified"}
        ],
        "acceptance_criteria": ["Data persists"],
        "selected_technologies": ["React", "Python", "SQLite"],
        "analysis_disclaimer": "Note: Requirements have not been tested."
    }

    response = client.post("/api/agents/development-planning", json={"requirement_analysis": req_data})
    assert response.status_code == 400
    assert "Gemini API key is not configured" in response.json()["detail"]


def test_planning_agent_success_mocked():
    """Verify end-to-end development planning with mocked provider response."""
    mock_plan = DevelopmentPlanResult(
        project_name="Task Tracker",
        architecture=ArchitectureOverview(
            pattern="Client-Server Single Page Application with REST Backend",
            description="React frontend communicating with FastAPI backend via HTTP/JSON.",
            frontend_responsibilities=["UI rendering", "State management", "Form handling"],
            backend_responsibilities=["Input validation", "SQLite CRUD operations", "API endpoints"],
            database_design="tasks table with columns: id (INTEGER PRIMARY KEY), title (TEXT), status (TEXT), created_at (TIMESTAMP)"
        ),
        file_tree=[
            "backend/app/main.py",
            "backend/app/database.py",
            "frontend/src/App.jsx",
            "frontend/src/components/TaskList.jsx"
        ],
        dependencies=[
            PlannedDependency(package_name="react", purpose="UI rendering", target="frontend"),
            PlannedDependency(package_name="fastapi", purpose="REST API", target="backend"),
            PlannedDependency(package_name="sqlite3", purpose="Database engine", target="backend")
        ],
        implementation_steps=[
            ImplementationStep(
                step_number=1,
                title="Database & Schema Setup",
                description="Initialize SQLite connection and create tasks table.",
                deliverables=["database.py", "initial schema migration"]
            ),
            ImplementationStep(
                step_number=2,
                title="API Endpoints Implementation",
                description="Implement CRUD routes for tasks.",
                deliverables=["routes.py", "CRUD tests"]
            )
        ],
        testing_strategy=[
            "Unit tests for database models",
            "Integration tests for REST endpoints",
            "Frontend component rendering tests"
        ],
        planning_disclaimer="Note: Architecture and plan are designed for implementation guidance. No code has been executed or generated yet."
    )

    with patch("app.agents.planning_agent.generate_structured", return_value=mock_plan):
        req_data = {
            "project_name": "Task Tracker",
            "project_objective": "Create an intuitive task management application.",
            "user_requirements": ["Track daily tasks"],
            "functional_requirements": ["Task CRUD"],
            "non_functional_requirements": ["Fast response"],
            "proposed_features": [
                {"name": "Task CRUD", "description": "Manage tasks", "source": "user_specified"}
            ],
            "acceptance_criteria": ["Data persists"],
            "selected_technologies": ["React", "Python", "SQLite"],
            "analysis_disclaimer": "Note: Requirements have not been tested."
        }

        response = client.post("/api/agents/development-planning", json={"requirement_analysis": req_data})
        assert response.status_code == 200
        data = response.json()
        assert data["project_name"] == "Task Tracker"
        assert data["architecture"]["pattern"] == "Client-Server Single Page Application with REST Backend"
        assert len(data["implementation_steps"]) == 2
        assert len(data["dependencies"]) == 3
        assert "No code has been executed" in data["planning_disclaimer"]
