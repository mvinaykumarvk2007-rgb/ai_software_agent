from typing import List
from app.schemas import (
    RequirementAnalysisRequest,
    RequirementAnalysisResult,
    FeatureSuggestion
)
from app.services.gemini_service import generate_structured

SYSTEM_PROMPT = """You are a senior software engineering requirement analysis agent.
Your mission is to perform an objective, structured requirement breakdown for a requested software project.

STRICT CONSTRAINTS:
1. Distinguish clearly between user-provided requirements and model-generated enhancements:
   - For every item in proposed_features, tag the 'source' attribute as strictly either 'user_specified' (if directly mentioned or implied by the user's prompt) or 'ai_suggested' (if it is an engineering recommendation from you).
   - In user_requirements, list only what the user explicitly requested.
2. Formulate concrete, testable functional and non-functional requirements.
3. Formulate clear, verifiable acceptance criteria.
4. You MUST include the mandatory analysis_disclaimer:
   "Note: Requirements and suggestions are generated for planning purposes and have not been tested or implemented."
5. Do NOT fabricate test results or claim that the requirements have been validated or tested against running code.
"""


def analyze_requirements(request: RequirementAnalysisRequest) -> RequirementAnalysisResult:
    """
    Executes the Requirement Analysis Agent.
    Accepts project name, requirements, and selected technologies, producing a validated RequirementAnalysisResult.
    """
    prompt = f"""Analyze the following software project:

Project Name: {request.project_name}
Target Technologies: {', '.join(request.selected_technologies)}
User-Provided Requirements:
\"\"\"
{request.requirements}
\"\"\"

Deconstruct this into:
1. Concise project objective.
2. User-provided requirements summary.
3. Specific functional requirements.
4. Non-functional requirements (security, performance, usability).
5. Proposed features clearly partitioned into 'user_specified' and 'ai_suggested'.
6. Verifiable acceptance criteria.
7. Explicit analysis disclaimer indicating these requirements have not been tested.
"""

    result = generate_structured(
        prompt=prompt,
        schema_cls=RequirementAnalysisResult,
        system_instruction=SYSTEM_PROMPT
    )

    # Ensure selected technologies and project name are consistent
    result.project_name = request.project_name
    result.selected_technologies = request.selected_technologies
    if not result.analysis_disclaimer:
        result.analysis_disclaimer = (
            "Note: Requirements and suggestions are generated for planning purposes and have not been tested or implemented."
        )

    return result
