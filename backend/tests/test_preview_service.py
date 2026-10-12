import json
import subprocess
from pathlib import Path

import pytest

from app.schemas import ProjectManifest
from app.services import preview_service
from app.services.preview_service import DockerUnavailableError


def test_preview_requires_docker(monkeypatch):
    monkeypatch.setattr(preview_service, "_find_docker_executable", lambda: None)

    with pytest.raises(DockerUnavailableError, match="Docker Desktop is required"):
        preview_service._require_docker()


def test_stage_project_uses_relative_api_proxy_without_changing_saved_files(
    tmp_path, monkeypatch
):
    file_contents = {
        "frontend/package.json": json.dumps({"scripts": {"dev": "vite"}}),
        "frontend/index.html": "<div id='root'></div>",
        "frontend/vite.config.js": "export default {};",
        "frontend/src/api.js": (
            "const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';"
        ),
        "backend/main.py": "app = object()",
        "backend/requirements.txt": "fastapi\nuvicorn\n",
    }
    manifest = ProjectManifest(
        project_id="preview-test",
        project_name="Preview test",
        target_stack="React + Python FastAPI + SQLite",
        created_at="2025-01-01T00:00:00+00:00",
        files_count=len(file_contents),
        total_bytes=1,
        file_paths=list(file_contents),
        generation_summary="Test project",
    )
    monkeypatch.setattr(
        preview_service, "get_project_manifest", lambda _project_id: manifest
    )
    monkeypatch.setattr(
        preview_service,
        "get_project_file_content",
        lambda _project_id, path: (file_contents[path], len(file_contents[path])),
    )

    staged = tmp_path / "staged"
    staged.mkdir()
    backend_kind = preview_service._stage_project("preview-test", staged)

    api_client = (staged / "frontend/src/api.js").read_text(encoding="utf-8")
    vite_config = (staged / "frontend/vite.preview.config.mjs").read_text(
        encoding="utf-8"
    )
    assert backend_kind == "python"
    assert "http://localhost:8000" not in api_client
    assert "'/api'" in vite_config
    assert file_contents["frontend/src/api.js"].endswith(
        "http://localhost:8000';"
    )


def test_stage_project_rejects_missing_runtime_files(tmp_path, monkeypatch):
    manifest = ProjectManifest(
        project_id="incomplete-project",
        project_name="Incomplete project",
        target_stack="React + Python FastAPI + SQLite",
        created_at="2025-01-01T00:00:00+00:00",
        files_count=0,
        total_bytes=0,
        file_paths=[],
        generation_summary="Test project",
    )
    monkeypatch.setattr(
        preview_service, "get_project_manifest", lambda _project_id: manifest
    )
    staging_dir = tmp_path / "staged"
    staging_dir.mkdir()

    with pytest.raises(preview_service.PreviewError, match="missing files"):
        preview_service._stage_project("incomplete-project", staging_dir)


def test_start_preview_keeps_readonly_project_mount_until_ready(tmp_path, monkeypatch):
    manifest = ProjectManifest(
        project_id="isolated-preview",
        project_name="Isolated preview",
        target_stack="React + Python FastAPI + SQLite",
        created_at="2025-01-01T00:00:00+00:00",
        files_count=1,
        total_bytes=1,
        file_paths=["README.md"],
        generation_summary="Test project",
    )
    monkeypatch.setattr(
        preview_service, "get_project_manifest", lambda _project_id: manifest
    )
    monkeypatch.setattr(preview_service, "get_project_dir", lambda _project_id: tmp_path)
    monkeypatch.setattr(preview_service, "_require_docker", lambda: None)
    monkeypatch.setattr(preview_service, "_ensure_runtime_image", lambda: None)

    def stage_project(_project_id, staging_dir):
        (staging_dir / "README.md").write_text("preview", encoding="utf-8")
        return "python"

    monkeypatch.setattr(preview_service, "_stage_project", stage_project)
    ports = iter([None, 43210])
    monkeypatch.setattr(
        preview_service, "_get_container_port", lambda _container_name: next(ports)
    )
    docker_run = []

    def run_docker(arguments, _timeout):
        docker_run.extend(arguments)
        return subprocess.CompletedProcess(arguments, 0, stdout="container-id", stderr="")

    monkeypatch.setattr(preview_service, "_run_docker", run_docker)

    def wait_until_ready(_container_name, preview_url):
        mount = docker_run[docker_run.index("--mount") + 1]
        staged_path = mount.split("source=", 1)[1].split(",target=", 1)[0]
        assert (Path(staged_path) / "README.md").is_file()
        assert preview_url == "http://127.0.0.1:43210"

    monkeypatch.setattr(preview_service, "_wait_until_ready", wait_until_ready)

    result = preview_service.start_project_preview("isolated-preview")

    assert result == {
        "project_id": "isolated-preview",
        "status": "running",
        "preview_url": "http://127.0.0.1:43210",
    }
    assert "readonly" in docker_run[docker_run.index("--mount") + 1]
    app_tmpfs = docker_run[docker_run.index("--tmpfs") + 3]
    assert app_tmpfs == "/app:rw,nosuid,nodev,exec,size=1g,uid=1000,gid=1000"
    assert docker_run[docker_run.index("--cap-drop") + 1] == "ALL"
    assert docker_run[docker_run.index("--security-opt") + 1] == "no-new-privileges:true"
