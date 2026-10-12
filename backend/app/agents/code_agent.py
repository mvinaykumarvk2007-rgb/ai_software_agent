from typing import List, Optional

from app.schemas import (
    CodeGenerationRequest,
    CodeGenerationBatch,
    CodeGenerationResult,
    GeneratedFile,
)
from app.services.gemini_service import (
    generate_structured,
    GeminiAPIError,
    GeminiMissingKeyError,
)
from app.services.project_storage import save_generated_project

SYSTEM_PROMPT = """You are a senior full-stack principal engineer and autonomous code generation agent.
Your mission is to generate a complete, working, modular full-stack codebase matching the validated requirements and development plan.

STRICT CONSTRAINTS & RULES:
1. Generate complete, syntactically correct source files for each layer (frontend, backend, database setup, dependencies, configuration, README).
2. The file 'path' MUST be a clean relative path using forward slashes (e.g. 'frontend/src/App.jsx', 'backend/main.py', 'README.md').
3. DO NOT use absolute paths, backslashes, drive letters, or directory traversal segments ('..').
4. The file 'content' MUST be raw source code text. DO NOT wrap the content in markdown backticks or code fences inside the string.
5. Provide realistic, runnable implementations with proper imports, API endpoint routes, error handling, state management, and SQLite schema creation.
6. Secrets & Environment Variables: NEVER hardcode API keys, passwords, or secrets. Always use environment variable placeholders (e.g. in .env.example).
7. Target the exact requested technology stack. DO NOT substitute unrequested frameworks.
8. Each file path in the files array MUST be unique.
9. Run both the backend and frontend on port 8000 and 5173 respectively. The backend must expose its REST routes below '/api'.
10. The frontend API client must use same-origin relative '/api' paths, never a hard-coded localhost URL.
11. Configure Vite to proxy '/api' requests to 'http://127.0.0.1:8000' and listen on host '0.0.0.0'.
12. Include a 'dev' script in frontend/package.json and use standard backend entrypoints: backend/main.py with a FastAPI 'app', or backend/server.js with a Node server.
"""


def determine_target_stack(selected_technologies: List[str]) -> str:
    """Determines whether to generate FastAPI+SQLite or Express+SQLite based on user selection."""
    has_node = "Node.js" in selected_technologies
    has_python = "Python" in selected_technologies

    if has_node and not has_python:
        return "React + Node.js Express + SQLite"
    return "React + Python FastAPI + SQLite"


def generate_code(request: CodeGenerationRequest) -> CodeGenerationResult:
    """
    Executes the Code Generation Agent.
    Accepts validated requirements and development plan, generates full-stack code,
    verifies file paths and contents, writes them to the workspace, and returns a CodeGenerationResult.
    """
    target_stack = determine_target_stack(request.selected_technologies)
    reqs = request.requirement_analysis
    plan = request.development_plan

    features_text = "\n".join([
        f"- [{f.source.upper()}] {f.name}: {f.description}"
        for f in reqs.proposed_features
    ])

    dependencies_text = "\n".join([
        f"- {d.package_name} ({d.target}): {d.purpose}"
        for d in plan.dependencies
    ])

    file_tree_text = "\n".join([f"- {fp}" for fp in plan.file_tree])

    prompt = f"""Generate a complete, working full-stack project for:

Project Name: {request.project_name}
Target Stack: {target_stack}
Objective: {reqs.project_objective}

Functional Requirements:
{chr(10).join([f'- {fr}' for fr in reqs.functional_requirements])}

Key Features:
{features_text}

Architecture Pattern:
{plan.architecture.pattern} - {plan.architecture.description}

Database Design:
{plan.architecture.database_design or 'SQLite database with relevant tables and relationships'}

Planned File Tree:
{file_tree_text}

Planned Dependencies:
{dependencies_text}

REQUIRED FILES TO GENERATE:
1. Frontend (React with Vite):
   - 'frontend/package.json'
   - 'frontend/index.html'
   - 'frontend/vite.config.js'
   - 'frontend/src/main.jsx'
   - 'frontend/src/App.jsx' (Interactive UI component with state and forms)
   - 'frontend/src/App.css' (Clean modern styling)
   - 'frontend/src/api.js' (HTTP client calling backend API)
   - Configure Vite's '/api' proxy to 'http://127.0.0.1:8000' for local and isolated previews.
2. Backend ({target_stack}):
   {"- 'backend/requirements.txt', 'backend/main.py', 'backend/database.py', 'backend/schemas.py'" if "FastAPI" in target_stack else "- 'backend/package.json', 'backend/server.js', 'backend/database.js'"}
   - Implement working REST endpoints matching the project objective.
   - Implement SQLite database table creation and basic CRUD operations.
   - Bind the backend on port 8000 and prefix all API routes with '/api'.
3. Config & Documentation:
   - '.env.example'
   - '.gitignore'
   - 'README.md' (Full instructions on how to set up, install dependencies, and run both frontend and backend)

Generate all files with complete, working code.
"""

    # Generation with 1 retry on malformed response
    batch: Optional[CodeGenerationBatch] = None
    last_err: Optional[Exception] = None

    for attempt in range(2):
        try:
            batch = generate_structured(
                prompt=prompt,
                schema_cls=CodeGenerationBatch,
                system_instruction=SYSTEM_PROMPT
            )
            break
        except GeminiMissingKeyError:
            raise
        except Exception as e:
            last_err = e
            if attempt == 0:
                # Add retry hint
                prompt += "\n\nIMPORTANT: Ensure JSON adheres strictly to schema, with valid relative file paths and no duplicate paths."
            else:
                raise GeminiAPIError(f"Code generation failed: {str(last_err)}")

    if not batch or not batch.files:
        raise GeminiAPIError("Code generation returned no files.")

    # Save to dedicated isolated workspace
    project_id, manifest = save_generated_project(
        project_name=request.project_name,
        target_stack=target_stack,
        generation_summary=batch.generation_summary,
        files=batch.files
    )

    return CodeGenerationResult(
        project_id=project_id,
        manifest=manifest,
        files=batch.files
    )
