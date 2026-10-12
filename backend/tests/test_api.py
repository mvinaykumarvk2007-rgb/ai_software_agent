import pytest
from fastapi.testclient import TestClient
from app.api import routes
from app.main import app
from app.services.preview_service import DockerUnavailableError

client = TestClient(app)


def test_health_check():
    """Verify that the health check endpoint returns 200 OK and healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai-software-engineer-backend"
    assert "timestamp" in data


def test_validate_project_success():
    """Verify that valid project specifications are accepted."""
    payload = {
        "project_name": "Task Manager App",
        "requirements": "Build a responsive task tracker with SQLite storage and REST endpoints.",
        "selected_technologies": ["React", "Python", "SQLite"]
    }
    response = client.post("/api/projects/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["project_name"] == "Task Manager App"
    assert set(data["selected_technologies"]) == {"React", "Python", "SQLite"}
    assert data["requirements_length"] == len(payload["requirements"])
    assert "workflow_initial_state" in data
    assert data["workflow_initial_state"]["Requirement Analysis"] == "Not started"
    assert data["workflow_initial_state"]["Planning"] == "Not started"
    assert data["workflow_initial_state"]["Code Generation"] == "Not started"
    assert data["workflow_initial_state"]["Testing"] == "Not started"
    assert data["workflow_initial_state"]["Website Preview"] == "Not started"
    assert data["workflow_initial_state"]["Debugging"] == "Not started"
    assert data["workflow_initial_state"]["Documentation"] == "Not started"


def test_validate_project_whitespace_name():
    """Verify that empty or whitespace-only project name is rejected with 422."""
    payload = {
        "project_name": "   ",
        "requirements": "Build a responsive task tracker with SQLite storage and REST endpoints.",
        "selected_technologies": ["React", "Python"]
    }
    response = client.post("/api/projects/validate", json=payload)
    assert response.status_code == 422


def test_validate_project_short_requirements():
    """Verify that requirements shorter than 10 characters are rejected with 422."""
    payload = {
        "project_name": "Task Manager",
        "requirements": "Too short",
        "selected_technologies": ["React"]
    }
    response = client.post("/api/projects/validate", json=payload)
    assert response.status_code == 422


def test_validate_project_no_technologies():
    """Verify that missing technology selection is rejected with 422."""
    payload = {
        "project_name": "Task Manager",
        "requirements": "Build a full stack application with proper testing and documentation.",
        "selected_technologies": []
    }
    response = client.post("/api/projects/validate", json=payload)
    assert response.status_code == 422


def test_validate_project_invalid_technology():
    """Verify that unapproved technology is rejected with 422."""
    payload = {
        "project_name": "Task Manager",
        "requirements": "Build a full stack application with proper testing and documentation.",
        "selected_technologies": ["React", "Rust", "Golang"]
    }
    response = client.post("/api/projects/validate", json=payload)
    assert response.status_code == 422
    assert "Invalid technology selection" in response.text


@pytest.mark.parametrize(
    "technologies",
    [
        ["React"],
        ["React", "Python"],
        ["React", "Python", "Node.js", "SQLite"],
        ["Python", "SQLite"],
    ],
)
def test_validate_project_rejects_unsupported_stack(technologies):
    response = client.post(
        "/api/projects/validate",
        json={
            "project_name": "Task Manager",
            "requirements": "Build a full stack task manager with persistent storage.",
            "selected_technologies": technologies,
        },
    )
    assert response.status_code == 422
    assert "Choose exactly one supported stack" in response.text


def test_cors_preflight():
    """Verify that CORS preflight from Vite dev server is allowed."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"
    }
    response = client.options("/api/projects/validate", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_start_preview_reports_missing_docker(monkeypatch):
    def raise_docker_unavailable(_project_id):
        raise DockerUnavailableError("Docker Desktop must be started.")

    monkeypatch.setattr(routes, "start_project_preview", raise_docker_unavailable)
    response = client.post("/api/projects/project-1/preview")

    assert response.status_code == 503
    assert response.json()["detail"] == "Docker Desktop must be started."
