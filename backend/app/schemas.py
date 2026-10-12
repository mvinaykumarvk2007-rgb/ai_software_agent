import re
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field, field_validator

ALLOWED_TECHNOLOGIES = {"React", "Python", "Node.js", "SQLite"}
SUPPORTED_TECHNOLOGY_STACKS = {
    frozenset({"React", "Python", "SQLite"}),
    frozenset({"React", "Node.js", "SQLite"}),
}


def validate_technology_stack(technologies: List[str]) -> List[str]:
    """Accept only technology combinations the code generator can produce."""
    normalized = list(dict.fromkeys(technologies))
    invalid = [technology for technology in normalized if technology not in ALLOWED_TECHNOLOGIES]
    if invalid:
        raise ValueError(
            f"Invalid technology selection: {', '.join(invalid)}. "
            f"Allowed options: {', '.join(sorted(ALLOWED_TECHNOLOGIES))}"
        )
    if frozenset(normalized) not in SUPPORTED_TECHNOLOGY_STACKS:
        raise ValueError(
            "Choose exactly one supported stack: React + Python + SQLite "
            "or React + Node.js + SQLite."
        )
    return normalized

WORKFLOW_STEPS = [
    "Requirement Analysis",
    "Planning",
    "Code Generation",
    "Testing",
    "Website Preview",
    "Debugging",
    "Documentation"
]

# --- Existing Foundation Models ---

class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    service: str = Field(..., json_schema_extra={"example": "ai-software-engineer-backend"})
    timestamp: str


class ProjectValidationRequest(BaseModel):
    project_name: str = Field(..., description="Project name", min_length=2, max_length=100)
    requirements: str = Field(..., description="Project requirements specification", min_length=10, max_length=10000)
    selected_technologies: List[str] = Field(..., description="List of chosen technologies")

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Project name cannot be empty or whitespace only.")
        return trimmed

    @field_validator("requirements")
    @classmethod
    def validate_requirements(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Requirements cannot be empty or whitespace only.")
        if len(trimmed) < 10:
            raise ValueError("Requirements description must be at least 10 characters.")
        return trimmed

    @field_validator("selected_technologies")
    @classmethod
    def validate_technologies(cls, v: List[str]) -> List[str]:
        return validate_technology_stack(v)


class ProjectValidationResponse(BaseModel):
    valid: bool
    message: str
    project_name: str
    requirements_length: int
    selected_technologies: List[str]
    workflow_initial_state: Dict[str, str]


# --- Agent 1: Requirement Analysis Models ---

class FeatureSuggestion(BaseModel):
    name: str = Field(..., description="Name of the feature")
    description: str = Field(..., description="Clear explanation of the feature")
    source: Literal["user_specified", "ai_suggested"] = Field(
        ..., description="Explicit source indicating user requirement vs AI enhancement"
    )


class RequirementAnalysisRequest(BaseModel):
    project_name: str = Field(..., min_length=2, max_length=100)
    requirements: str = Field(..., min_length=10, max_length=10000)
    selected_technologies: List[str] = Field(...)

    @field_validator("project_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Project name cannot be empty.")
        return trimmed

    @field_validator("requirements")
    @classmethod
    def clean_requirements(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 10:
            raise ValueError("Requirements must be at least 10 characters.")
        return trimmed

    @field_validator("selected_technologies")
    @classmethod
    def check_techs(cls, v: List[str]) -> List[str]:
        return validate_technology_stack(v)


class RequirementAnalysisResult(BaseModel):
    project_name: str
    project_objective: str
    user_requirements: List[str] = Field(
        default_factory=list,
        description="Direct requirements specified by the user"
    )
    functional_requirements: List[str] = Field(
        default_factory=list,
        description="Core functional expectations for the software"
    )
    non_functional_requirements: List[str] = Field(
        default_factory=list,
        description="Performance, reliability, usability, and security requirements"
    )
    proposed_features: List[FeatureSuggestion] = Field(
        default_factory=list,
        description="Features explicitly categorized by user_specified vs ai_suggested"
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Verifiable acceptance criteria"
    )
    selected_technologies: List[str]
    analysis_disclaimer: str = Field(
        default="Note: Requirements and suggestions are generated for planning purposes and have not been tested or implemented.",
        description="Mandatory disclaimer that requirements have not been tested"
    )


# --- Agent 2: Development Planning Models ---

class ArchitectureOverview(BaseModel):
    pattern: str = Field(..., description="High-level architectural pattern, e.g. Modular REST SPA")
    description: str = Field(..., description="Architecture explanation")
    frontend_responsibilities: List[str] = Field(default_factory=list)
    backend_responsibilities: List[str] = Field(default_factory=list)
    database_design: Optional[str] = Field(None, description="Database schema and entity relationships")


class PlannedDependency(BaseModel):
    package_name: str
    purpose: str
    target: Literal["frontend", "backend"]


class ImplementationStep(BaseModel):
    step_number: int
    title: str
    description: str
    deliverables: List[str] = Field(default_factory=list)


class DevelopmentPlanningRequest(BaseModel):
    requirement_analysis: RequirementAnalysisResult


class DevelopmentPlanResult(BaseModel):
    project_name: str
    architecture: ArchitectureOverview
    file_tree: List[str] = Field(
        default_factory=list,
        description="Projected directory structure"
    )
    dependencies: List[PlannedDependency] = Field(
        default_factory=list,
        description="Frontend and backend dependencies required"
    )
    implementation_steps: List[ImplementationStep] = Field(
        default_factory=list,
        description="Ordered implementation steps"
    )
    testing_strategy: List[str] = Field(
        default_factory=list,
        description="Planned unit, integration, and manual testing approach"
    )
    planning_disclaimer: str = Field(
        default="Note: Architecture and plan are designed for implementation guidance. No code has been executed or generated yet.",
        description="Mandatory disclaimer that code has not been generated or executed"
    )


# --- Agent 3: Code Generation Models ---

class GeneratedFile(BaseModel):
    path: str = Field(..., description="Relative file path, e.g. frontend/src/App.jsx")
    content: str = Field(..., description="Complete source code text of the file", max_length=500000)
    description: Optional[str] = Field(None, description="Brief note on file responsibility")

    @field_validator("path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        trimmed = v.strip().replace("\\", "/")
        if not trimmed:
            raise ValueError("File path cannot be empty.")
        if trimmed.startswith("/"):
            raise ValueError(f"Absolute path '{v}' is forbidden. Path must be relative.")
        if ":" in trimmed:
            raise ValueError(f"Drive letter or scheme in '{v}' is forbidden.")
        parts = [p for p in trimmed.split("/") if p]
        if any(p == ".." for p in parts):
            raise ValueError(f"Directory traversal segment ('..') in '{v}' is strictly prohibited.")
        # Only allow safe path characters
        for part in parts:
            if not re.match(r"^[\w\-.]+$", part):
                raise ValueError(f"Unsafe characters in path component '{part}' of '{v}'.")
        return "/".join(parts)


class CodeGenerationBatch(BaseModel):
    files: List[GeneratedFile] = Field(..., description="List of generated source files")
    generation_summary: str = Field(..., description="Executive summary of the generated codebase")

    @field_validator("files")
    @classmethod
    def validate_files_list(cls, v: List[GeneratedFile]) -> List[GeneratedFile]:
        if not v:
            raise ValueError("Code generation produced no files.")
        seen_paths = set()
        for f in v:
            normalized = f.path.lower()
            if normalized in seen_paths:
                raise ValueError(f"Duplicate file path '{f.path}' detected in generated code batch.")
            seen_paths.add(normalized)
        return v


class CodeGenerationRequest(BaseModel):
    project_name: str = Field(..., min_length=2, max_length=100)
    requirements: str = Field(..., min_length=10, max_length=10000)
    selected_technologies: List[str] = Field(...)
    requirement_analysis: RequirementAnalysisResult
    development_plan: DevelopmentPlanResult

    @field_validator("selected_technologies")
    @classmethod
    def check_technologies(cls, v: List[str]) -> List[str]:
        return validate_technology_stack(v)


class ProjectManifest(BaseModel):
    project_id: str
    project_name: str
    target_stack: str
    created_at: str
    files_count: int
    total_bytes: int
    file_paths: List[str]
    generation_summary: str
    generation_disclaimer: str = Field(
        default="Note: Code has been generated according to plan specifications. Code has not been automatically executed or deployed.",
        description="Mandatory disclaimer that code has not been executed"
    )


class CodeGenerationResult(BaseModel):
    project_id: str
    manifest: ProjectManifest
    files: List[GeneratedFile]


class FileContentResponse(BaseModel):
    path: str
    content: str
    size_bytes: int


class ProjectFilesResponse(BaseModel):
    project_id: str
    project_name: str
    target_stack: str
    files: List[str]
    total_files: int


# --- Agent 4: Testing Models ---

CheckStatus = Literal["passed", "failed", "skipped", "blocked"]
CheckCategory = Literal["structural", "syntax", "dependency", "security", "build", "runtime"]


class TestCaseResult(BaseModel):
    name: str = Field(..., description="Check name")
    category: CheckCategory
    status: CheckStatus
    duration_ms: float
    message: str
    details: Optional[str] = None


class TestReportSummary(BaseModel):
    """Convenience sub-object so the frontend can read report.summary.failed, .passed, etc."""
    passed: int
    failed: int
    skipped: int
    blocked: int
    total: int
    overall_status: CheckStatus


class TestReport(BaseModel):
    project_id: str
    project_name: str
    target_stack: str
    tested_at: str
    total_checks: int
    passed_count: int
    failed_count: int
    skipped_count: int
    blocked_count: int
    overall_status: CheckStatus
    summary: TestReportSummary           # convenience sub-object consumed by frontend
    checks: List[TestCaseResult]
    environment_info: Dict[str, str] = Field(default_factory=dict)


class TestProjectRequest(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=100)

    @field_validator("project_id")
    @classmethod
    def validate_pid(cls, v: str) -> str:
        clean = v.strip()
        if not clean or not re.match(r"^[a-zA-Z0-9_\-]+$", clean):
            raise ValueError(f"Invalid project ID format: '{v}'")
        return clean


class DebugFinding(BaseModel):
    check_name: str
    category: CheckCategory
    priority: Literal["high", "medium", "low"]
    summary: str
    evidence: str
    recommended_action: str


class DebuggingReport(BaseModel):
    project_id: str
    project_name: str
    analyzed_at: str
    status: Literal["clean", "issues_found"]
    summary: str
    findings: List[DebugFinding] = Field(default_factory=list)
    test_report: TestReport


class DocumentationResult(BaseModel):
    project_id: str
    project_name: str
    file_path: str
    content: str
    manifest: ProjectManifest
