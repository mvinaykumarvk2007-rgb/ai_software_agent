import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Optional

from app.services.project_storage import (
    ProjectNotFoundError,
    UnsafePathError,
    get_project_dir,
    get_project_file_content,
    get_project_manifest,
    validate_project_id,
)

DOCKER_INFO_TIMEOUT_S = 5
DOCKER_COMMAND_TIMEOUT_S = 20
DOCKER_BUILD_TIMEOUT_S = 300
PREVIEW_READY_TIMEOUT_S = 300
PREVIEW_PORT = 5173
PREVIEW_IMAGE = "ai-software-engineer-preview:1"
PREVIEW_RUNTIME_DIR = Path(__file__).with_name("preview_runtime")

_preview_lock = threading.Lock()


class PreviewError(Exception):
    """Raised when a generated project cannot be previewed safely."""


class DockerUnavailableError(PreviewError):
    """Raised when Docker is not installed or its daemon is unavailable."""


class PreviewStartupError(PreviewError):
    """Raised when the generated app fails to start in its container."""


def _find_docker_executable() -> Optional[str]:
    docker_path = shutil.which("docker")
    if docker_path:
        return docker_path

    install_roots = []
    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles")
        local_app_data = os.environ.get("LOCALAPPDATA")
        if program_files:
            install_roots.append(Path(program_files))
        if local_app_data:
            install_roots.append(Path(local_app_data) / "Programs")

    for root in install_roots:
        candidate = root / "Docker" / "Docker" / "resources" / "bin" / "docker.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def _run_docker(arguments: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [_find_docker_executable() or "docker", *arguments],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise PreviewError(f"Docker command timed out after {timeout} seconds.") from error
    except OSError as error:
        raise DockerUnavailableError(f"Could not start Docker: {error}") from error


def _require_docker() -> None:
    if not _find_docker_executable():
        raise DockerUnavailableError(
            "Docker Desktop is required to safely run generated websites. "
            "Install and start Docker Desktop, then try Preview again."
        )

    result = _run_docker(["info"], DOCKER_INFO_TIMEOUT_S)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise DockerUnavailableError(
            "Docker Desktop is installed but its engine is not running. "
            + (details[:1000] if details else "Start Docker Desktop and try again.")
        )


def _container_name(project_id: str) -> str:
    clean_id = validate_project_id(project_id).lower()
    safe_id = re.sub(r"[^a-z0-9_-]", "-", clean_id)
    return f"ai-preview-{safe_id}"


def _ensure_runtime_image() -> None:
    dockerfile = PREVIEW_RUNTIME_DIR / "Dockerfile"
    if not dockerfile.is_file():
        raise PreviewStartupError("The trusted preview runtime Dockerfile is missing.")
    result = _run_docker(
        ["build", "--tag", PREVIEW_IMAGE, str(PREVIEW_RUNTIME_DIR)],
        DOCKER_BUILD_TIMEOUT_S,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise PreviewStartupError(
            "Could not prepare the isolated preview container. "
            + (details[-4000:] if details else "Docker image build failed.")
        )


def _get_container_port(container_name: str) -> Optional[int]:
    state = _run_docker(
        ["inspect", "--format", "{{.State.Running}}", container_name],
        DOCKER_COMMAND_TIMEOUT_S,
    )
    if state.returncode != 0:
        return None
    if state.stdout.strip() != "true":
        _run_docker(["rm", "--force", container_name], DOCKER_COMMAND_TIMEOUT_S)
        return None

    port_result = _run_docker(
        ["port", container_name, f"{PREVIEW_PORT}/tcp"],
        DOCKER_COMMAND_TIMEOUT_S,
    )
    if port_result.returncode != 0:
        return None
    match = re.search(r"127\.0\.0\.1:(\d+)", port_result.stdout)
    return int(match.group(1)) if match else None


def _stage_project(project_id: str, staging_dir: Path) -> str:
    manifest = get_project_manifest(project_id)
    if "React" not in manifest.target_stack:
        raise PreviewError("Only generated React websites can be previewed.")

    normalized_paths = {path.replace("\\", "/") for path in manifest.file_paths}
    required_paths = {
        "frontend/package.json",
        "frontend/index.html",
        "frontend/vite.config.js",
    }
    if "FastAPI" in manifest.target_stack:
        required_paths.update({"backend/main.py", "backend/requirements.txt"})
        backend_kind = "python"
    elif "Node.js" in manifest.target_stack or "Express" in manifest.target_stack:
        required_paths.update({"backend/server.js", "backend/package.json"})
        backend_kind = "node"
    else:
        raise PreviewError(f"Unsupported project stack: {manifest.target_stack}")

    missing = sorted(required_paths - normalized_paths)
    if missing:
        raise PreviewError(
            "This project is missing files needed for a live preview: "
            + ", ".join(missing)
        )

    for relative_path in manifest.file_paths:
        normalized = relative_path.replace("\\", "/")
        target = staging_dir.joinpath(*PurePosixPath(normalized).parts)
        if not target.resolve().is_relative_to(staging_dir.resolve()):
            raise UnsafePathError(f"Generated file path escapes the project: {relative_path}")
        content, _ = get_project_file_content(project_id, normalized)
        if normalized.startswith("frontend/") and normalized.endswith(
            (".js", ".jsx", ".ts", ".tsx", ".json", ".env")
        ):
            content = content.replace("http://localhost:8000", "")
            content = content.replace("http://127.0.0.1:8000", "")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    package_file = staging_dir / "frontend" / "package.json"
    try:
        package = json.loads(package_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PreviewError(f"Frontend package.json is invalid: {error}") from error
    if not isinstance(package.get("scripts"), dict) or not package["scripts"].get("dev"):
        raise PreviewError("The generated frontend must define an npm 'dev' script.")

    preview_config = staging_dir / "frontend" / "vite.preview.config.mjs"
    preview_config.write_text(
        """import { mergeConfig, defineConfig } from 'vite';
import generatedConfig from './vite.config.js';

export default defineConfig(async (environment) => {
  const base = typeof generatedConfig === 'function'
    ? await generatedConfig(environment)
    : generatedConfig;
  return mergeConfig(base || {}, {
    server: {
      host: '0.0.0.0',
      port: 5173,
      strictPort: true,
      proxy: {
        ...(base?.server?.proxy || {}),
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  });
});
""",
        encoding="utf-8",
    )

    return backend_kind


def _container_start_script(backend_kind: str) -> str:
    if backend_kind == "python":
        backend_install = (
            "python3 -m venv /app/.venv && "
            "/app/.venv/bin/pip install --no-cache-dir -r requirements.txt && "
            "/app/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 "
            ">/tmp/backend.log 2>&1 &"
        )
    else:
        backend_install = (
            "npm install --no-audit --no-fund && "
            "PORT=8000 HOST=127.0.0.1 node server.js >/tmp/backend.log 2>&1 &"
        )

    return f"""set -eu
cp -R /workspace/. /app/
export npm_config_cache=/tmp/npm-cache
cd /app/frontend
npm install --no-audit --no-fund
cd /app/backend
{backend_install}
ready=
for attempt in $(seq 1 90); do
  if python3 -c 'import socket; s=socket.create_connection(("127.0.0.1", 8000), timeout=1); s.close()'; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" != 1 ]; then
  cat /tmp/backend.log
  exit 1
fi
cd /app/frontend
npm run dev -- --config vite.preview.config.mjs --host 0.0.0.0 --port 5173 \\
  >/tmp/frontend.log 2>&1 &
wait
"""


def _read_container_logs(container_name: str) -> str:
    result = _run_docker(["logs", container_name], DOCKER_COMMAND_TIMEOUT_S)
    return (result.stdout + result.stderr).strip()[-6000:]


def _wait_until_ready(container_name: str, preview_url: str) -> None:
    deadline = time.monotonic() + PREVIEW_READY_TIMEOUT_S
    last_error = "The preview did not return a successful response."

    while time.monotonic() < deadline:
        state = _run_docker(
            ["inspect", "--format", "{{.State.Running}}", container_name],
            DOCKER_COMMAND_TIMEOUT_S,
        )
        if state.returncode != 0 or state.stdout.strip() != "true":
            logs = _read_container_logs(container_name)
            raise PreviewStartupError(
                "The generated app stopped while starting."
                + (f"\n\nContainer output:\n{logs}" if logs else "")
            )
        try:
            with urllib.request.urlopen(preview_url, timeout=2) as response:
                if 200 <= response.status < 400:
                    return
        except (OSError, urllib.error.URLError) as error:
            last_error = str(error)
        time.sleep(2)

    logs = _read_container_logs(container_name)
    raise PreviewStartupError(
        f"Preview did not become ready within {PREVIEW_READY_TIMEOUT_S} seconds: {last_error}"
        + (f"\n\nContainer output:\n{logs}" if logs else "")
    )


def start_project_preview(project_id: str) -> dict[str, str]:
    """Starts the generated website in a resource-limited Docker container."""
    manifest = get_project_manifest(project_id)
    project_dir = get_project_dir(project_id)
    if not project_dir.is_dir():
        raise ProjectNotFoundError(f"Project '{project_id}' not found.")

    container_name = _container_name(manifest.project_id)
    with _preview_lock:
        _require_docker()

        existing_port = _get_container_port(container_name)
        if existing_port:
            return {
                "project_id": manifest.project_id,
                "status": "running",
                "preview_url": f"http://127.0.0.1:{existing_port}",
            }

        _ensure_runtime_image()
        with tempfile.TemporaryDirectory(prefix="ai-preview-") as temporary_dir:
            staging_dir = Path(temporary_dir)
            backend_kind = _stage_project(manifest.project_id, staging_dir)
            run_args = [
                "run",
                "--detach",
                "--name",
                container_name,
                "--label",
                "ai-software-engineering.preview=true",
                "--label",
                f"ai-software-engineering.project={manifest.project_id}",
                "--read-only",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,size=256m",
                "--tmpfs",
                "/app:rw,nosuid,nodev,exec,size=1g,uid=1000,gid=1000",
                "--mount",
                f"type=bind,source={staging_dir.resolve()},target=/workspace,readonly",
                "--publish",
                f"127.0.0.1::{PREVIEW_PORT}",
                "--network",
                "bridge",
                "--memory",
                "1g",
                "--cpus",
                "2",
                "--pids-limit",
                "256",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                "--user",
                "1000:1000",
                PREVIEW_IMAGE,
                "sh",
                "-lc",
                _container_start_script(backend_kind),
            ]
            started = _run_docker(run_args, DOCKER_COMMAND_TIMEOUT_S)
            if started.returncode != 0:
                details = (started.stderr or started.stdout).strip()
                raise PreviewStartupError(
                    "Docker could not start the isolated app container. "
                    + (details[:2000] if details else "No details were returned by Docker.")
                )

            port = _get_container_port(container_name)
            if not port:
                logs = _read_container_logs(container_name)
                _run_docker(["rm", "--force", container_name], DOCKER_COMMAND_TIMEOUT_S)
                raise PreviewStartupError(
                    "Docker started the preview container but did not publish its local website port."
                    + (f"\n\nContainer output:\n{logs}" if logs else "")
                )

            preview_url = f"http://127.0.0.1:{port}"
            try:
                _wait_until_ready(container_name, preview_url)
            except PreviewError:
                _run_docker(["rm", "--force", container_name], DOCKER_COMMAND_TIMEOUT_S)
                raise

            return {
                "project_id": manifest.project_id,
                "status": "running",
                "preview_url": preview_url,
            }


def stop_project_preview(project_id: str) -> dict[str, str]:
    """Stops and removes a project's preview container."""
    manifest = get_project_manifest(project_id)
    container_name = _container_name(manifest.project_id)
    with _preview_lock:
        _require_docker()
        result = _run_docker(["rm", "--force", container_name], DOCKER_COMMAND_TIMEOUT_S)
        if result.returncode != 0 and "No such container" not in result.stderr:
            details = (result.stderr or result.stdout).strip()
            raise PreviewError(
                "Could not stop the preview container. "
                + (details[:1000] if details else "Docker returned an unknown error.")
            )
    return {"project_id": manifest.project_id, "status": "stopped"}
