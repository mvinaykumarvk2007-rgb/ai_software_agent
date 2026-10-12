import io
import os
import re
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from app.schemas import GeneratedFile, ProjectManifest

STORAGE_BASE_DIR = Path(
    os.getenv(
        "PROJECT_STORAGE_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "generated_projects"),
    )
).resolve()


class ProjectNotFoundError(Exception):
    """Raised when the specified project ID does not exist."""
    pass


class UnsafePathError(Exception):
    """Raised when an unsafe file path or directory traversal is detected."""
    pass


def get_storage_dir() -> Path:
    """Ensures and returns the base directory for generated projects."""
    STORAGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    return STORAGE_BASE_DIR


def validate_project_id(project_id: str) -> str:
    """Validates that project_id is a secure alphanumeric or UUID string."""
    clean_id = project_id.strip()
    if not clean_id or not re.match(r"^[a-zA-Z0-9_\-]+$", clean_id):
        raise ProjectNotFoundError(f"Invalid project ID format: '{project_id}'")
    return clean_id


def get_project_dir(project_id: str) -> Path:
    """Returns the resolved project directory path."""
    clean_id = validate_project_id(project_id)
    project_dir = (get_storage_dir() / clean_id).resolve()
    if not project_dir.is_relative_to(get_storage_dir()):
        raise UnsafePathError("Directory traversal detected in project ID.")
    return project_dir


def save_generated_project(
    project_name: str,
    target_stack: str,
    generation_summary: str,
    files: List[GeneratedFile],
    project_id: Optional[str] = None
) -> Tuple[str, ProjectManifest]:
    """
    Saves a set of validated generated files into a dedicated workspace.
    Writes files with UTF-8 encoding and persists manifest.json.
    """
    pid = project_id or str(uuid.uuid4())
    project_dir = get_project_dir(pid)
    project_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: List[str] = []
    total_bytes = 0

    for f in files:
        # Resolve target file path securely
        target_path = (project_dir / f.path).resolve()
        if not target_path.is_relative_to(project_dir):
            raise UnsafePathError(f"File path '{f.path}' attempts directory traversal.")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        content_bytes = f.content.encode("utf-8")
        target_path.write_bytes(content_bytes)

        saved_paths.append(f.path)
        total_bytes += len(content_bytes)

    manifest = ProjectManifest(
        project_id=pid,
        project_name=project_name,
        target_stack=target_stack,
        created_at=datetime.now(timezone.utc).isoformat(),
        files_count=len(saved_paths),
        total_bytes=total_bytes,
        file_paths=sorted(saved_paths),
        generation_summary=generation_summary,
        generation_disclaimer=(
            "Note: Code has been generated according to plan specifications. "
            "Code has not been automatically executed or deployed."
        )
    )

    # Save manifest.json in the project root
    manifest_path = project_dir / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    return pid, manifest


def get_project_manifest(project_id: str) -> ProjectManifest:
    """Loads and returns the ProjectManifest for a given project ID."""
    project_dir = get_project_dir(project_id)
    manifest_path = project_dir / "manifest.json"
    if not manifest_path.exists():
        raise ProjectNotFoundError(f"Project '{project_id}' not found.")

    try:
        data = manifest_path.read_text(encoding="utf-8")
        return ProjectManifest.model_validate_json(data)
    except Exception as e:
        raise ProjectNotFoundError(f"Failed to read manifest for '{project_id}': {str(e)}")


def list_project_files(project_id: str) -> List[str]:
    """Returns the list of relative file paths in the generated project."""
    manifest = get_project_manifest(project_id)
    return manifest.file_paths


def get_project_file_content(project_id: str, relative_path: str) -> Tuple[str, int]:
    """
    Safely retrieves the content and size of a specific generated file.
    Returns (content_str, size_bytes).
    """
    project_dir = get_project_dir(project_id)
    if not project_dir.exists():
        raise ProjectNotFoundError(f"Project '{project_id}' not found.")

    clean_rel = relative_path.strip().replace("\\", "/").lstrip("/")
    if ".." in clean_rel.split("/"):
        raise UnsafePathError(f"Directory traversal prohibited: '{relative_path}'")

    target_path = (project_dir / clean_rel).resolve()
    if not target_path.is_relative_to(project_dir):
        raise UnsafePathError(f"Target path escapes project directory: '{relative_path}'")

    if not target_path.is_file():
        raise ProjectNotFoundError(f"File '{clean_rel}' not found in project '{project_id}'.")

    content = target_path.read_text(encoding="utf-8")
    size_bytes = target_path.stat().st_size
    return content, size_bytes


def save_project_documentation(project_id: str, content: str) -> str:
    """Persist generated documentation and keep the project manifest in sync."""
    project_dir = get_project_dir(project_id)
    manifest = get_project_manifest(project_id)
    documentation = GeneratedFile(
        path="docs/PROJECT_GUIDE.md",
        content=content,
        description="Generated project setup and architecture guide",
    )
    target_path = (project_dir / documentation.path).resolve()
    if not target_path.is_relative_to(project_dir):
        raise UnsafePathError("Documentation path escapes the project directory.")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(documentation.content, encoding="utf-8")
    manifest.file_paths = sorted(set(manifest.file_paths) | {documentation.path})
    manifest.files_count = len(manifest.file_paths)
    total_bytes = 0
    for path in manifest.file_paths:
        saved_path = (project_dir / path).resolve()
        if not saved_path.is_relative_to(project_dir):
            raise UnsafePathError(f"Manifest path escapes project directory: '{path}'")
        if saved_path.is_file():
            total_bytes += saved_path.stat().st_size
    manifest.total_bytes = total_bytes
    (project_dir / "manifest.json").write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )
    return documentation.path


def create_project_zip_buffer(project_id: str) -> io.BytesIO:
    """
    Generates an in-memory ZIP archive of the entire generated project folder.
    """
    project_dir = get_project_dir(project_id)
    if not project_dir.exists():
        raise ProjectNotFoundError(f"Project '{project_id}' not found.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                rel_archive_path = file_path.relative_to(project_dir).as_posix()
                zip_file.write(file_path, arcname=rel_archive_path)

    zip_buffer.seek(0)
    return zip_buffer
