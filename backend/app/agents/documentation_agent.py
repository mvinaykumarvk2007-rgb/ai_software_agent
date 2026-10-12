from app.schemas import DocumentationResult
from app.services.project_storage import get_project_manifest, save_project_documentation


def generate_project_documentation(project_id: str) -> DocumentationResult:
    manifest = get_project_manifest(project_id)
    if "FastAPI" in manifest.target_stack:
        backend_setup = """```powershell
cd backend
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`."""
        backend_docs = "FastAPI interactive API documentation is available at `http://127.0.0.1:8000/docs`."
    else:
        backend_setup = """```powershell
cd backend
npm install
npm run dev
```"""
        backend_docs = "Review the backend README and route files for the available API endpoints."

    file_tree = "\n".join(f"- `{path}`" for path in manifest.file_paths)
    content = f"""# {manifest.project_name} - Project Guide

## Overview

{manifest.generation_summary}

- **Stack:** {manifest.target_stack}
- **Generated:** {manifest.created_at}
- **Project ID:** `{manifest.project_id}`

## Prerequisites

- Node.js 20 or newer and npm
- Python 3.11 or newer for the FastAPI stack
- SQLite (included with Python; the Node stack uses its declared SQLite package)

## Run locally

Start the backend in one terminal:

{backend_setup}

Start the React frontend in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local address printed by Vite (normally `http://localhost:5173`). The Vite
configuration proxies `/api` requests to the backend on port 8000.

## API and database

{backend_docs}

The application stores its data in SQLite. Review the backend database and model
files for the schema and initialization behavior. Keep credentials and environment
specific values in local environment files; do not commit secrets.

## Verification

Run the backend tests, if present, from the backend directory:

```powershell
python -m pytest
```

Build the frontend to catch compile-time issues:

```powershell
cd frontend
npm run build
```

## Project files

{file_tree}

## Existing documentation

See the project `README.md` for any project-specific setup notes supplied during
code generation. This guide is generated from the saved project manifest and
standard stack commands; verify environment-specific commands before deployment.
"""
    file_path = save_project_documentation(project_id, content)
    return DocumentationResult(
        project_id=manifest.project_id,
        project_name=manifest.project_name,
        file_path=file_path,
        content=content,
        manifest=get_project_manifest(project_id),
    )
