from datetime import datetime, timezone
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.schemas import (
    HealthResponse,
    ProjectValidationRequest,
    ProjectValidationResponse,
    RequirementAnalysisRequest,
    RequirementAnalysisResult,
    DevelopmentPlanningRequest,
    DevelopmentPlanResult,
    CodeGenerationRequest,
    CodeGenerationResult,
    ProjectManifest,
    ProjectFilesResponse,
    FileContentResponse,
    TestReport,
    TestReportSummary,
    TestProjectRequest,
    DebuggingReport,
    DocumentationResult,
    WORKFLOW_STEPS,
)
from app.agents.requirement_agent import analyze_requirements
from app.agents.planning_agent import create_development_plan
from app.agents.code_agent import generate_code
from app.agents.debugging_agent import debug_project
from app.agents.documentation_agent import generate_project_documentation
from app.agents.testing_agent import (
    run_project_tests,
    get_latest_test_report,
    ReportNotFoundError,
)
from app.services.gemini_service import GeminiMissingKeyError, GeminiAPIError
from app.services.project_storage import (
    get_project_manifest,
    list_project_files,
    get_project_file_content,
    create_project_zip_buffer,
    ProjectNotFoundError,
    UnsafePathError,
)
from app.services.preview_service import (
    DockerUnavailableError,
    PreviewError,
    PreviewStartupError,
    start_project_preview,
    stop_project_preview,
)

router = APIRouter()


# --- Foundation Endpoints ---

@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Backend Health Check",
    description="Returns backend service status and current UTC timestamp."
)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="ai-software-engineer-backend",
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.post(
    "/projects/validate",
    response_model=ProjectValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Project Input",
    description="Validates project name, requirements text, and selected tech stack."
)
async def validate_project(payload: ProjectValidationRequest) -> ProjectValidationResponse:
    initial_workflow = {step: "Not started" for step in WORKFLOW_STEPS}

    return ProjectValidationResponse(
        valid=True,
        message="Project parameters validated successfully. Ready for agent orchestration.",
        project_name=payload.project_name,
        requirements_length=len(payload.requirements),
        selected_technologies=payload.selected_technologies,
        workflow_initial_state=initial_workflow
    )


# --- Agent Endpoints ---

@router.post(
    "/agents/requirement-analysis",
    response_model=RequirementAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Run Requirement Analysis Agent",
    description="Parses project goals, extracts user vs suggested requirements, and produces structured analysis."
)
def run_requirement_agent(payload: RequirementAnalysisRequest) -> RequirementAnalysisResult:
    try:
        return analyze_requirements(payload)
    except GeminiMissingKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except GeminiAPIError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during requirement analysis: {str(e)}"
        )


@router.post(
    "/agents/development-planning",
    response_model=DevelopmentPlanResult,
    status_code=status.HTTP_200_OK,
    summary="Run Development Planning Agent",
    description="Takes validated requirement analysis and synthesizes an architectural plan, file tree, dependencies, and roadmap."
)
def run_planning_agent(payload: DevelopmentPlanningRequest) -> DevelopmentPlanResult:
    try:
        return create_development_plan(payload)
    except GeminiMissingKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except GeminiAPIError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during development planning: {str(e)}"
        )


@router.post(
    "/agents/code-generation",
    response_model=CodeGenerationResult,
    status_code=status.HTTP_200_OK,
    summary="Run Code Generation Agent",
    description="Consumes requirement analysis and development plan to generate and save a complete full-stack codebase."
)
def run_code_agent(payload: CodeGenerationRequest) -> CodeGenerationResult:
    try:
        return generate_code(payload)
    except GeminiMissingKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except GeminiAPIError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    except (UnsafePathError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error in generated project files: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during code generation: {str(e)}"
        )


@router.post(
    "/agents/testing",
    response_model=TestReport,
    status_code=status.HTTP_200_OK,
    summary="Run Testing Agent",
    description="Executes structural, static syntax, AST, dependency, and isolated runtime tests on a generated project."
)
def run_testing_agent(payload: TestProjectRequest) -> TestReport:
    try:
        return run_project_tests(payload.project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnsafePathError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during project testing: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/test",
    response_model=TestReport,
    status_code=status.HTTP_200_OK,
    summary="Test Project by ID",
    description="Executes verification checks on a project identified by project_id."
)
def test_project(project_id: str) -> TestReport:
    try:
        return run_project_tests(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnsafePathError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during project testing: {str(e)}"
        )


@router.post(
    "/projects/{project_id}/preview",
    status_code=status.HTTP_200_OK,
    summary="Start Isolated Project Preview",
    description="Runs a generated website in a resource-limited Docker container."
)
def start_preview(project_id: str) -> dict[str, str]:
    try:
        return start_project_preview(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnsafePathError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DockerUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except PreviewStartupError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except PreviewError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/projects/{project_id}/preview",
    status_code=status.HTTP_200_OK,
    summary="Stop Isolated Project Preview",
    description="Stops and removes the Docker container for a generated website preview."
)
def stop_preview(project_id: str) -> dict[str, str]:
    try:
        return stop_project_preview(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DockerUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except PreviewError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get(
    "/projects/{project_id}/test-report",
    response_model=TestReport,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Test Report",
    description="Retrieves the most recent test report generated for a project."
)
def get_test_report(project_id: str) -> TestReport:
    try:
        return get_latest_test_report(project_id)
    except (ProjectNotFoundError, ReportNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnsafePathError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/projects/{project_id}/debug",
    response_model=DebuggingReport,
    status_code=status.HTTP_200_OK,
    summary="Run Project Debugging Agent",
    description="Analyzes failed or blocked verification checks and recommends targeted fixes.",
)
def debug_generated_project(
    project_id: str,
) -> DebuggingReport:
    try:
        return debug_project(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnsafePathError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during project debugging: {str(e)}",
        )


@router.post(
    "/projects/{project_id}/documentation",
    response_model=DocumentationResult,
    status_code=status.HTTP_200_OK,
    summary="Generate Project Documentation",
    description="Creates a project-specific setup guide and adds it to the project archive.",
)
def document_generated_project(project_id: str) -> DocumentationResult:
    try:
        return generate_project_documentation(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnsafePathError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during documentation generation: {str(e)}",
        )


# --- Project Retrieval & Download Endpoints ---

@router.get(
    "/projects/{project_id}/manifest",
    response_model=ProjectManifest,
    status_code=status.HTTP_200_OK,
    summary="Get Project Manifest",
    description="Retrieves the metadata and file manifest for a generated project."
)
def get_manifest(project_id: str) -> ProjectManifest:
    try:
        return get_project_manifest(project_id)
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnsafePathError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/projects/{project_id}/files",
    response_model=ProjectFilesResponse,
    status_code=status.HTTP_200_OK,
    summary="List Generated Project Files",
    description="Returns the list of relative file paths for a generated project."
)
def list_files(project_id: str) -> ProjectFilesResponse:
    try:
        manifest = get_project_manifest(project_id)
        files = list_project_files(project_id)
        return ProjectFilesResponse(
            project_id=project_id,
            project_name=manifest.project_name,
            target_stack=manifest.target_stack,
            files=files,
            total_files=len(files)
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnsafePathError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/projects/{project_id}/files/{file_path:path}",
    response_model=FileContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get File Content",
    description="Reads the text content of a specific generated file."
)
def get_file(project_id: str, file_path: str) -> FileContentResponse:
    try:
        content, size = get_project_file_content(project_id, file_path)
        return FileContentResponse(
            path=file_path,
            content=content,
            size_bytes=size
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnsafePathError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/projects/{project_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download Project as ZIP",
    description="Packages the generated project folder into a ZIP file for download."
)
def download_project_zip(project_id: str):
    try:
        manifest = get_project_manifest(project_id)
        zip_buffer = create_project_zip_buffer(project_id)
        safe_name = quote(manifest.project_name.replace(" ", "_"))

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}.zip"'
            }
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnsafePathError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
