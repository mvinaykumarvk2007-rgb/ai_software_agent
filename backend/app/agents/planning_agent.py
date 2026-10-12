from app.schemas import (
    DevelopmentPlanningRequest,
    DevelopmentPlanResult,
    ArchitectureOverview,
    PlannedDependency,
    ImplementationStep
)
from app.services.gemini_service import generate_structured

SYSTEM_PROMPT = """You are a senior full-stack software architect agent.
Your mission is to synthesize a practical, modular technical implementation plan based on validated project requirements.

STRICT CONSTRAINTS:
1. Provide an architectural pattern that directly supports the selected technologies and requirements.
2. Outline explicit separation of concerns between frontend and backend responsibilities.
3. Design a normalized database schema or entity structure appropriate for the technologies (e.g. SQLite tables if SQLite is selected).
4. Provide a realistic file tree structure showing organized source code folders.
5. List essential dependencies with target ('frontend' or 'backend') and concise rationale.
6. Provide chronological, numbered implementation steps with concrete deliverables.
7. Outline a comprehensive testing strategy (unit tests, API integration tests, manual checks).
8. You MUST include the mandatory planning_disclaimer:
   "Note: Architecture and plan are designed for implementation guidance. No code has been executed or generated yet."
9. Do NOT claim that files have been created or that code has been executed.
"""


def create_development_plan(request: DevelopmentPlanningRequest) -> DevelopmentPlanResult:
    """
    Executes the Development Planning Agent.
    Accepts validated RequirementAnalysisResult and produces a comprehensive DevelopmentPlanResult.
    """
    reqs = request.requirement_analysis

    features_summary = "\n".join([
        f"- [{f.source.upper()}] {f.name}: {f.description}"
        for f in reqs.proposed_features
    ])

    acceptance_summary = "\n".join([f"- {ac}" for ac in reqs.acceptance_criteria])

    prompt = f"""Create a technical development plan for:

Project: {reqs.project_name}
Objective: {reqs.project_objective}
Technologies: {', '.join(reqs.selected_technologies)}

Functional Requirements:
{chr(10).join([f'- {fr}' for fr in reqs.functional_requirements])}

Non-Functional Requirements:
{chr(10).join([f'- {nfr}' for nfr in reqs.non_functional_requirements])}

Key Features:
{features_summary}

Acceptance Criteria:
{acceptance_summary}

Produce:
1. Architectural pattern and detailed description.
2. Clear division of frontend vs backend responsibilities.
3. Database design (e.g. tables, relations, columns if applicable).
4. Projected file tree directory layout.
5. Key dependencies for frontend and backend.
6. Step-by-step implementation milestones with deliverables.
7. Verification & testing strategy.
8. Mandatory planning disclaimer.
"""

    result = generate_structured(
        prompt=prompt,
        schema_cls=DevelopmentPlanResult,
        system_instruction=SYSTEM_PROMPT
    )

    result.project_name = reqs.project_name
    if not result.planning_disclaimer:
        result.planning_disclaimer = (
            "Note: Architecture and plan are designed for implementation guidance. No code has been executed or generated yet."
        )

    return result
