# AI Website Builder with Autonomous Engineering Agents

Describe an app in ordinary language, let the agents analyze, plan, generate, and test it, then open the finished website in a live local preview. Generated apps are run in a Docker container, not directly on the host.

---

## 🏛 System Architecture

```
ai-software-engineer/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application & CORS configuration
│   │   ├── schemas.py          # Pydantic schemas for validation, agents, files & test reports
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py       # Health, validation, agent triggers, file/ZIP & test endpoints
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── requirement_agent.py # Agent 1: Requirement Analysis module
│   │   │   ├── planning_agent.py    # Agent 2: Development Planning module
│   │   │   ├── code_agent.py        # Agent 3: Code Generation module
│   │   │   └── testing_agent.py     # Agent 4: Verification & Static Analysis module
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── gemini_service.py    # Official Google Gen AI SDK client & error handlers
│   │       ├── project_storage.py   # Isolated generated-project workspace & ZIP packaging
│   │       ├── preview_service.py   # Starts and stops resource-limited Docker previews
│   │       └── preview_runtime/
│   │           └── Dockerfile       # Trusted runtime image for generated apps
│   ├── generated_projects/      # Isolated project workspaces (ignored by Git)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_api.py          # Pytest suite for foundation endpoints & CORS
│   │   ├── test_agents.py       # Pytest suite for Agent 1 & Agent 2
│   │   ├── test_code_generation.py # Pytest suite for Agent 3, ZIP export & file security
│   │   └── test_testing_agent.py   # Pytest suite for Agent 4 verification checks
│   ├── requirements.txt         # FastAPI, Uvicorn, Pydantic, Pytest, HTTPX, google-genai
│   ├── .env.example             # Configuration template
│   └── .env                     # Local secrets (never committed to Git)
├── frontend/
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx          # Dashboard top bar with title & live status
│   │   │   ├── Sidebar.jsx         # Navigation & platform details
│   │   │   ├── StatusIndicator.jsx # Live backend ping indicator
│   │   │   ├── TechSelector.jsx    # React, Python, Node.js, SQLite selector
│   │   │   ├── WorkflowPanel.jsx   # 6-step agent workflow with action controls
│   │   │   └── ResultsArea.jsx     # Agent results, test report, and live website preview
│   │   ├── services/
│   │   │   └── api.js              # Fetch client for all API endpoints
│   │   ├── App.jsx                 # Dashboard state & orchestration
│   │   ├── App.css                 # Dark theme component styles
│   │   ├── index.css               # Design tokens, typography, resets
│   │   └── main.jsx                # React root mount
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚡ Supported Full-Stack Technology Stacks

The Code Generation Agent supports generating complete codebases for these two supported selections:
1. **React + Python FastAPI + SQLite**:
   - Frontend: Vite + React SPA with components, API client, and CSS.
   - Backend: Python FastAPI with REST routes, Pydantic models, and SQLite database setup.
   - Docs & Config: `.env.example`, `.gitignore`, `README.md`.
2. **React + Node.js Express + SQLite**:
   - Frontend: Vite + React SPA with components, API client, and CSS.
   - Backend: Node.js with Express, CORS, and SQLite database setup.
   - Docs & Config: `.env.example`, `.gitignore`, `README.md`.

React and SQLite are required in both options, and exactly one backend runtime must be selected.

---

## 🔑 AI Integration & Configuration

This project integrates the Gemini API using the official **Google Gen AI SDK** (`google-genai`).

### Setting Up Your Environment
1. Copy `.env.example` to `.env` in `backend/`:
   ```powershell
   Copy-Item "d:\ai studio\ai-software-engineer\.env.example" "d:\ai studio\ai-software-engineer\backend\.env"
   ```
2. Open `backend\.env` and set your API key from [Google AI Studio](https://aistudio.google.com/):
   ```env
   GEMINI_API_KEY=AIzaSy...your_gemini_api_key...
   GEMINI_MODEL=gemini-3.8-flash
   ```

For hosted deployments, configure `GEMINI_API_KEY` as a private backend environment
variable in the hosting provider. Never put the key in frontend variables or commit it.

---

## 🚀 Setup & Execution Guide (Windows PowerShell)

Open Windows PowerShell:

Install and start [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) before creating a live website preview. If Docker is unavailable, the builder explains how to fix it and will not run generated code directly on Windows.

### 1. Backend Setup & Verification
```powershell
# 1. Navigate to backend directory
cd "d:\ai studio\ai-software-engineer\backend"

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run automated test suite (uses mocked AI responses; no paid API calls)
pytest tests -v

# 5. Start the FastAPI development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup & Verification
In a **separate Windows PowerShell terminal**:
```powershell
# 1. Navigate to frontend directory
cd "d:\ai studio\ai-software-engineer\frontend"

# 2. Run production build check
npm run build

# 3. Start the Vite development server
npm run dev
```

---

## 🖥 End-to-End Workflow

1. Open [http://localhost:5173](http://localhost:5173) in your browser.
2. Enter your project name and requirements, and choose your technology stack.
3. Click **"Build My Website"**. The builder automatically runs requirement analysis, planning, code generation, and verification in order.
4. When those agents finish, the **Website Preview** step starts the generated frontend and backend in Docker and opens the **Website** tab. View it in the builder or open it in another browser tab.
5. The preview uses a local-only address on your computer; it is not a public/shareable deployment. Click **"Stop preview"** when you are done.
6. The **Test Report** tab shows structural, syntax, dependency, and security checks. The **Code** tab and ZIP download remain available if you want to inspect or keep the generated project.
7. The **Debugging** step analyzes failed verification checks and shows targeted recommendations; it does not alter generated source files automatically.
8. The **Documentation** step creates `docs/PROJECT_GUIDE.md`, adds it to the project file list and ZIP download, and shows it in the Documentation tab.

The first preview may take a few minutes while Docker downloads the trusted runtime and installs the generated app's dependencies. Network access is needed during this setup.

## ☁️ Public Deployment on Render

The root `render.yaml` defines a public Render Static Site for the frontend and a
Python Web Service for the API. Connect this repository to Render and deploy the
Blueprint; then add `GEMINI_API_KEY` in the API service's **Environment** settings
before using AI generation. The sample Blueprint uses the default Render hostnames
`ai-software-engineer-web.onrender.com` and `ai-software-engineer-api.onrender.com`;
if you change either service name, update `VITE_API_BASE_URL` on the Static Site
and `CORS_ORIGINS` on the API service to match the assigned HTTPS URLs. The
GitHub Pages workflow defaults to `https://ai-software-engineer-api.onrender.com`;
set the GitHub Actions repository variable `VITE_API_BASE_URL` if Render assigns a
different backend hostname.

The sample uses Render's free web-service plan and local generated-project storage.
That storage is temporary: generated projects can be lost when the service restarts
or redeploys. Do not rely on it for long-term storage; download generated projects
as ZIP files. The public API uses your Gemini key for visitor requests, so set
provider-side quota/budget limits and monitor usage.

The **Website Preview** Docker container is intended for a local builder install.
Render's web service does not provide a Docker daemon to this app, so this preview
step will report that Docker is unavailable when the builder itself is hosted.
To share a generated website publicly, deploy that generated app separately to a
web host; a local preview URL is not accessible from other computers.

## 🌐 GitHub Pages Frontend

The `.github/workflows/static.yml` workflow builds `frontend/` and publishes its
Vite output to GitHub Pages, including the repository subpath
`/ai_software_agent/`. Replace the repository's existing root-upload Pages
workflow with this file and push the complete project (especially `frontend/`,
`backend/`, and `.github/workflows/static.yml`) to its `main` branch.

GitHub Pages hosts only static files, not the FastAPI backend. To enable health
checks and AI generation, deploy the backend separately (for example, to Render),
then add a GitHub Actions repository variable named `VITE_API_BASE_URL` containing
the backend's HTTPS origin (for example, `https://your-api.onrender.com`). Configure
the backend's `CORS_ORIGINS` environment variable with
`https://mvinaykumarvk2007-rgb.github.io`. Without a deployed backend the page can
load, but builder API features will remain offline. Never expose `GEMINI_API_KEY`
as a `VITE_` variable or in the static frontend.

---

## 🧪 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health status and timestamp |
| `POST` | `/api/projects/validate` | Validates project input parameters |
| `POST` | `/api/agents/requirement-analysis` | **Agent 1**: Extracts structured requirements |
| `POST` | `/api/agents/development-planning` | **Agent 2**: Synthesizes architecture and roadmap |
| `POST` | `/api/agents/code-generation` | **Agent 3**: Generates and persists full-stack codebase |
| `POST` | `/api/projects/{id}/test` | **Agent 4**: Runs verification checks on generated project |
| `POST` | `/api/projects/{id}/preview` | Starts an isolated local website preview and returns its URL |
| `DELETE` | `/api/projects/{id}/preview` | Stops and removes the website preview container |
| `POST` | `/api/projects/{id}/debug` | Analyzes verification results and returns actionable diagnostic findings |
| `POST` | `/api/projects/{id}/documentation` | Generates and saves a project-specific setup guide |
| `POST` | `/api/agents/testing` | **Agent 4**: Alias endpoint accepting `project_id` payload |
| `GET` | `/api/projects/{id}/test-report` | Retrieves latest `test_report.json` for a project |
| `GET` | `/api/projects/{id}/manifest` | Retrieves manifest and file list for generated project |
| `GET` | `/api/projects/{id}/files` | Lists all relative file paths in project |
| `GET` | `/api/projects/{id}/files/{path}` | Retrieves source code for a specific generated file |
| `GET` | `/api/projects/{id}/download` | Downloads full project folder as a ZIP archive |
| `GET` | `/docs` | Interactive Swagger API documentation |

---

## 🔒 Security & Sandbox Isolation

- **Host Protection & Sandbox Policy**: Generated website code is never run directly on the host. A preview runs in a Docker container with a read-only source mount, read-only container root, dropped Linux capabilities, no-new-privileges, CPU/memory/process limits, and ports bound only to loopback. The container has outbound network access while installing dependencies and while running the app; Docker isolation reduces risk but is not equivalent to a separate VM.
- **Docker is required for live preview**: If Docker Desktop is missing or stopped, the preview reports an actionable error and does not execute generated files on Windows.
- **Trusted Internal Identifiers**: All test endpoints accept only validated internal project UUIDs. Direct user-supplied filesystem paths are strictly rejected.
- **Path Sanitization**: Every file path is validated to reject directory traversal (`..`), absolute paths, or invalid characters.
- **Isolated Storage**: All generated code is written to `backend/generated_projects/<project_id>/` and cannot overwrite the assistant's own code or host files.
- **Secret Protection**: Generated configuration files use placeholder environment variables (`.env.example`) and undergo automated secret-leak auditing.
