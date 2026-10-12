"""
Testing Agent – Milestone 5 (Final Verification)
=================================================
Runs a multi-category verification suite against a generated full-stack project.

Safety guarantees
-----------------
* Untrusted code is NEVER executed directly on the host.
* Python syntax is validated in-process via ast.parse() — compile only, no exec/eval.
* The only subprocess calls permitted are:
    - docker info   — probe daemon availability (DOCKER_INFO_TIMEOUT_S timeout)
  Generated frontend build scripts are never executed directly on the host.
  Docker probes run with a hard timeout and test runs are concurrency-limited.
* No pip install, no python execution, no Docker image builds.

Concurrency
-----------
At most MAX_CONCURRENT_TEST_JOBS test runs execute simultaneously.  Additional
requests wait for a slot (up to SUBPROCESS_DEFAULT_TIMEOUT_S seconds).
"""

import ast
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.schemas import (
    CheckStatus,
    TestCaseResult,
    TestReport,
    TestReportSummary,
)
from app.services.project_storage import (
    ProjectNotFoundError,
    UnsafePathError,
    get_project_dir,
    get_project_manifest,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CONCURRENT_TEST_JOBS: int = 3
DOCKER_INFO_TIMEOUT_S: int = 4
SUBPROCESS_DEFAULT_TIMEOUT_S: int = 60

_test_semaphore = threading.Semaphore(MAX_CONCURRENT_TEST_JOBS)


# ---------------------------------------------------------------------------
# Custom errors
# ---------------------------------------------------------------------------

class ReportNotFoundError(Exception):
    """Raised when no test report exists for a given project."""
    pass


# ---------------------------------------------------------------------------
# Environment probes
# ---------------------------------------------------------------------------

def is_docker_available() -> Tuple[bool, str]:
    """Checks whether the docker CLI and daemon are operational."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False, "Docker executable not found on PATH."
    try:
        proc = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=DOCKER_INFO_TIMEOUT_S,
        )
        if proc.returncode == 0:
            return True, "Docker daemon is running and responsive."
        return False, f"docker info exited {proc.returncode} – daemon may be inactive."
    except subprocess.TimeoutExpired:
        return False, f"docker info timed out after {DOCKER_INFO_TIMEOUT_S}s."
    except Exception as e:
        return False, f"Failed to probe Docker daemon: {str(e)}"


def _is_tool_available(name: str) -> bool:
    return bool(shutil.which(name))


# ---------------------------------------------------------------------------
# Static analysis helpers
# ---------------------------------------------------------------------------

def check_brackets_balance(code: str) -> Optional[str]:
    """Simple parser checking matching brackets in JS/JSX source code."""
    stack: List[Tuple[str, int]] = []
    pairs = {')': '(', '}': '{', ']': '['}

    for line_no, line in enumerate(code.splitlines(), start=1):
        in_single = in_double = in_backtick = escaped = False
        for char in line:
            if escaped:
                escaped = False
                continue
            if char == '\\':
                escaped = True
                continue
            if char == "'" and not in_double and not in_backtick:
                in_single = not in_single
                continue
            if char == '"' and not in_single and not in_backtick:
                in_double = not in_double
                continue
            if char == '`' and not in_single and not in_double:
                in_backtick = not in_backtick
                continue
            if in_single or in_double or in_backtick:
                continue
            if char in "({[":
                stack.append((char, line_no))
            elif char in ")}]":
                if not stack:
                    return f"Unmatched closing bracket '{char}' on line {line_no}."
                open_char, open_line = stack.pop()
                if pairs[char] != open_char:
                    return (
                        f"Mismatched bracket '{char}' on line {line_no} "
                        f"(expected '{open_char}' from line {open_line})."
                    )

    if stack:
        unclosed, unclosed_line = stack[-1]
        return f"Unclosed bracket '{unclosed}' opened on line {unclosed_line}."
    return None


# ---------------------------------------------------------------------------
# Check builder
# ---------------------------------------------------------------------------

def _check(
    name: str,
    category: str,
    status: str,
    message: str,
    duration_ms: float,
    details: Optional[str] = None,
) -> TestCaseResult:
    return TestCaseResult(
        name=name,
        category=category,      # type: ignore[arg-type]
        status=status,          # type: ignore[arg-type]
        duration_ms=round(duration_ms, 2),
        message=message,
        details=details,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_project_tests(project_id: str) -> TestReport:
    """
    Executes the full verification suite for a generated project.

    Acquires a semaphore slot before running; raises RuntimeError if all
    MAX_CONCURRENT_TEST_JOBS slots are occupied after waiting
    SUBPROCESS_DEFAULT_TIMEOUT_S seconds.
    """
    acquired = _test_semaphore.acquire(timeout=SUBPROCESS_DEFAULT_TIMEOUT_S)
    if not acquired:
        raise RuntimeError(
            f"Testing agent is at capacity ({MAX_CONCURRENT_TEST_JOBS} concurrent jobs). "
            "Please retry in a moment."
        )
    try:
        return _run_all_checks(project_id)
    finally:
        _test_semaphore.release()


# ---------------------------------------------------------------------------
# Internal – all checks
# ---------------------------------------------------------------------------

def _run_all_checks(project_id: str) -> TestReport:  # noqa: C901
    project_dir = get_project_dir(project_id)
    if not project_dir.exists():
        raise ProjectNotFoundError(f"Project '{project_id}' not found.")

    manifest = get_project_manifest(project_id)
    checks: List[TestCaseResult] = []

    is_fastapi = "FastAPI" in manifest.target_stack
    is_express = "Express" in manifest.target_stack or (
        "Node" in manifest.target_stack and "FastAPI" not in manifest.target_stack
    )

    # Environment probes (done once, reported in env_info)
    docker_ok, docker_msg = is_docker_available()
    node_ok = _is_tool_available("node")
    npm_ok = _is_tool_available("npm")

    env_info: Dict[str, str] = {
        "python_version": sys.version.split()[0],
        "node_installed": str(node_ok),
        "npm_installed": str(npm_ok),
        "docker_available": str(docker_ok),
        "docker_status": docker_msg,
    }

    # =========================================================================
    # 1. STRUCTURAL – manifest integrity
    # =========================================================================
    t0 = time.perf_counter()
    if manifest.files_count > 0 and len(manifest.file_paths) == manifest.files_count:
        checks.append(_check(
            "Manifest Integrity", "structural", "passed",
            f"Manifest verified: {manifest.files_count} file(s), stack: {manifest.target_stack}.",
            (time.perf_counter() - t0) * 1000,
            f"Target stack: {manifest.target_stack}",
        ))
    else:
        checks.append(_check(
            "Manifest Integrity", "structural", "failed",
            "Manifest file-count mismatch.",
            (time.perf_counter() - t0) * 1000,
            f"Recorded: {len(manifest.file_paths)}, declared: {manifest.files_count}",
        ))

    # =========================================================================
    # 2. STRUCTURAL – core entrypoints
    # =========================================================================
    t0 = time.perf_counter()
    missing: List[str] = []

    if is_fastapi:
        if not (
            (project_dir / "backend" / "main.py").exists()
            or (project_dir / "main.py").exists()
        ):
            missing.append("backend/main.py")
    if is_express:
        if not (
            (project_dir / "backend" / "server.js").exists()
            or (project_dir / "server.js").exists()
        ):
            missing.append("backend/server.js")

    if not (project_dir / "frontend" / "package.json").exists():
        missing.append("frontend/package.json")

    if not missing:
        checks.append(_check(
            "Core Entrypoint Structure", "structural", "passed",
            f"All required entrypoints exist for {manifest.target_stack}.",
            (time.perf_counter() - t0) * 1000,
        ))
    else:
        checks.append(_check(
            "Core Entrypoint Structure", "structural", "failed",
            f"Missing entrypoints: {', '.join(missing)}",
            (time.perf_counter() - t0) * 1000,
            "Generated codebase does not conform to the required layout.",
        ))

    # =========================================================================
    # 3. SYNTAX – Python AST compilation
    # =========================================================================
    t0 = time.perf_counter()
    py_files = list(project_dir.rglob("*.py"))
    py_errors: List[str] = []

    for py_file in py_files:
        rel = py_file.relative_to(project_dir).as_posix()
        try:
            ast.parse(py_file.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as e:
            py_errors.append(f"{rel} (line {e.lineno}): {e.msg}")
        except Exception as e:
            py_errors.append(f"{rel}: {e}")

    checks.append(_check(
        "Python AST Syntax Validation",
        "syntax",
        "passed" if not py_errors else "failed",
        (
            f"AST compilation passed on {len(py_files)} Python file(s)."
            if not py_errors
            else f"Syntax error(s) in {len(py_errors)} Python file(s)."
        ) if py_files else "No Python files present (passed).",
        (time.perf_counter() - t0) * 1000,
        "\n".join(py_errors) if py_errors else None,
    ))

    # =========================================================================
    # 4. SYNTAX – JSON files
    # =========================================================================
    t0 = time.perf_counter()
    json_files = list(project_dir.rglob("*.json"))
    json_errors: List[str] = []

    for jf in json_files:
        rel = jf.relative_to(project_dir).as_posix()
        try:
            json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            json_errors.append(f"{rel}: {e}")

    checks.append(_check(
        "JSON Syntax & Integrity",
        "syntax",
        "passed" if not json_errors else "failed",
        (
            f"Validated {len(json_files)} JSON file(s)."
            if not json_errors
            else f"Invalid JSON in {len(json_errors)} file(s)."
        ),
        (time.perf_counter() - t0) * 1000,
        "\n".join(json_errors) if json_errors else None,
    ))

    # =========================================================================
    # 5. SYNTAX – JavaScript / JSX bracket balance
    # =========================================================================
    t0 = time.perf_counter()
    js_files = [p for p in project_dir.rglob("*") if p.suffix in (".js", ".jsx")]
    js_errors: List[str] = []

    for js_file in js_files:
        rel = js_file.relative_to(project_dir).as_posix()
        try:
            err = check_brackets_balance(js_file.read_text(encoding="utf-8"))
            if err:
                js_errors.append(f"{rel}: {err}")
        except Exception as e:
            js_errors.append(f"{rel}: {e}")

    checks.append(_check(
        "JavaScript / JSX Structural Syntax",
        "syntax",
        "passed" if not js_errors else "failed",
        (
            f"Bracket balance validated across {len(js_files)} JS/JSX file(s)."
            if not js_errors
            else f"Bracket mismatch in {len(js_errors)} JS/JSX file(s)."
        ),
        (time.perf_counter() - t0) * 1000,
        "\n".join(js_errors) if js_errors else None,
    ))

    # =========================================================================
    # 6. DEPENDENCY – requirements.txt audit (FastAPI stack)
    # =========================================================================
    if is_fastapi:
        t0 = time.perf_counter()
        req_txt = project_dir / "backend" / "requirements.txt"
        if not req_txt.exists():
            req_txt = project_dir / "requirements.txt"  # monorepo fallback

        if req_txt.exists():
            content_lower = req_txt.read_text(encoding="utf-8").lower()
            missing_deps = [
                p for p in ("fastapi", "uvicorn") if p not in content_lower
            ]
            checks.append(_check(
                "Backend requirements.txt Audit",
                "dependency",
                "passed" if not missing_deps else "failed",
                (
                    "requirements.txt present with fastapi & uvicorn declared."
                    if not missing_deps
                    else f"requirements.txt missing package(s): {', '.join(missing_deps)}."
                ),
                (time.perf_counter() - t0) * 1000,
                f"File: {req_txt.relative_to(project_dir).as_posix()}",
            ))
        else:
            checks.append(_check(
                "Backend requirements.txt Audit",
                "dependency",
                "skipped",
                "requirements.txt not present in backend/ or project root; dependency validation deferred.",
                (time.perf_counter() - t0) * 1000,
                "This project snapshot does not include a generated dependency manifest yet.",
            ))

    # =========================================================================
    # 7. DEPENDENCY – backend package.json audit (Express stack)
    # =========================================================================
    if is_express:
        t0 = time.perf_counter()
        be_pkg = project_dir / "backend" / "package.json"
        if not be_pkg.exists():
            be_pkg = project_dir / "package.json"  # monorepo fallback

        if be_pkg.exists():
            try:
                be_data = json.loads(be_pkg.read_text(encoding="utf-8"))
                all_be_deps = {
                    **be_data.get("dependencies", {}),
                    **be_data.get("devDependencies", {}),
                }
                missing_be = [p for p in ("express",) if p not in all_be_deps]
                checks.append(_check(
                    "Backend Package Specification (Express)",
                    "dependency",
                    "passed" if not missing_be else "failed",
                    (
                        "express declared in backend package.json."
                        if not missing_be
                        else f"backend package.json missing: {', '.join(missing_be)}."
                    ),
                    (time.perf_counter() - t0) * 1000,
                    f"File: {be_pkg.relative_to(project_dir).as_posix()}",
                ))
            except Exception as e:
                checks.append(_check(
                    "Backend Package Specification (Express)",
                    "dependency", "failed",
                    f"Failed to parse backend package.json: {e}",
                    (time.perf_counter() - t0) * 1000,
                ))
        else:
            checks.append(_check(
                "Backend Package Specification (Express)",
                "dependency", "failed",
                "backend/package.json not found for Express stack.",
                (time.perf_counter() - t0) * 1000,
            ))

    # =========================================================================
    # 8. DEPENDENCY – frontend package.json audit (both stacks)
    # =========================================================================
    t0 = time.perf_counter()
    fe_pkg = project_dir / "frontend" / "package.json"
    if fe_pkg.exists():
        try:
            fe_data = json.loads(fe_pkg.read_text(encoding="utf-8"))
            all_fe_deps = {
                **fe_data.get("dependencies", {}),
                **fe_data.get("devDependencies", {}),
            }
            scripts = fe_data.get("scripts", {})
            missing_fe = []
            if "react" not in all_fe_deps:
                missing_fe.append("react")
            if "build" not in scripts:
                missing_fe.append("scripts.build")

            checks.append(_check(
                "Frontend Package Specification",
                "dependency",
                "passed" if not missing_fe else "failed",
                (
                    "React dependency and build script are defined."
                    if not missing_fe
                    else f"frontend/package.json missing: {', '.join(missing_fe)}."
                ),
                (time.perf_counter() - t0) * 1000,
                f"Dependencies: {', '.join(list(all_fe_deps.keys())[:6])}",
            ))
        except Exception as e:
            checks.append(_check(
                "Frontend Package Specification",
                "dependency", "failed",
                f"Failed to parse frontend/package.json: {e}",
                (time.perf_counter() - t0) * 1000,
            ))
    else:
        checks.append(_check(
            "Frontend Package Specification",
            "dependency", "failed",
            "frontend/package.json is missing.",
            (time.perf_counter() - t0) * 1000,
        ))

    # =========================================================================
    # 9. SECURITY – secret / environment safety audit
    # =========================================================================
    t0 = time.perf_counter()
    env_example = project_dir / ".env.example"
    secret_patterns = [
        (r"AIza[0-9A-Za-z\-_]{35}", "Google API key"),
        (r"sk-[a-zA-Z0-9]{40,}", "OpenAI API key"),
        (r"(?i)password\s*=\s*['\"]?\w{8,}", "Hardcoded password"),
        (r"(?i)secret\s*=\s*['\"]?\w{8,}", "Hardcoded secret"),
    ]

    if env_example.exists():
        env_content = env_example.read_text(encoding="utf-8")
        found_secrets = [
            label for pattern, label in secret_patterns if re.search(pattern, env_content)
        ]
        checks.append(_check(
            "Secret & Environment Safety Audit",
            "security",
            "failed" if found_secrets else "passed",
            (
                f"Potential credentials in .env.example: {', '.join(found_secrets)}."
                if found_secrets
                else ".env.example contains placeholder values only – no real credentials detected."
            ),
            (time.perf_counter() - t0) * 1000,
            "Remove hardcoded keys from generated config." if found_secrets else None,
        ))
    else:
        checks.append(_check(
            "Secret & Environment Safety Audit",
            "security", "passed",
            "No .env.example present – no credentials to audit.",
            (time.perf_counter() - t0) * 1000,
        ))

    # =========================================================================
    # 10. BUILD – generated scripts are not executed on the host
    # =========================================================================
    t0 = time.perf_counter()

    if not fe_pkg.exists():
        checks.append(_check(
            "Frontend Production Build",
            "build", "skipped",
            "Skipped: frontend/package.json not found.",
            (time.perf_counter() - t0) * 1000,
        ))
    else:
        checks.append(_check(
            "Frontend Production Build",
            "build", "blocked",
            "Blocked: generated frontend build scripts are not executed directly on the host.",
            (time.perf_counter() - t0) * 1000,
            "Run this check only inside a disposable, isolated environment.",
        ))

    # =========================================================================
    # 11. RUNTIME – containerised isolation check
    # =========================================================================
    t0 = time.perf_counter()
    if not docker_ok:
        checks.append(_check(
            "Containerized Runtime Isolation",
            "runtime", "blocked",
            "Runtime execution blocked: Docker is not installed or the daemon is inactive.",
            (time.perf_counter() - t0) * 1000,
            (
                "Host Security Enforcement: untrusted generated code is strictly prohibited "
                "from running directly on the host OS without container isolation. "
                f"Docker probe: {docker_msg}. "
                "Install Docker Desktop and start the daemon to enable containerised test runs."
            ),
        ))
        checks.append(_check(
            "Backend Unit Test Execution",
            "runtime", "blocked",
            "Blocked: requires an isolated Docker container runtime.",
            0.0,
            "Untrusted backend code was not executed on the host.",
        ))
    else:
        checks.append(_check(
            "Containerized Runtime Isolation",
            "runtime", "skipped",
            "Container runtime available; Docker-based test execution deferred to a future milestone.",
            (time.perf_counter() - t0) * 1000,
            "Use docker-compose or a manual container invocation to verify full integration.",
        ))

    # =========================================================================
    # Totals, summary, overall status
    # =========================================================================
    passed_count = sum(1 for c in checks if c.status == "passed")
    failed_count = sum(1 for c in checks if c.status == "failed")
    blocked_count = sum(1 for c in checks if c.status == "blocked")
    skipped_count = sum(1 for c in checks if c.status == "skipped")

    if failed_count > 0:
        overall: CheckStatus = "failed"
    elif blocked_count > 0 and passed_count == 0:
        overall = "blocked"
    else:
        overall = "passed"

    summary = TestReportSummary(
        passed=passed_count,
        failed=failed_count,
        skipped=skipped_count,
        blocked=blocked_count,
        total=len(checks),
        overall_status=overall,
    )

    report = TestReport(
        project_id=project_id,
        project_name=manifest.project_name,
        target_stack=manifest.target_stack,
        tested_at=datetime.now(timezone.utc).isoformat(),
        total_checks=len(checks),
        passed_count=passed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        blocked_count=blocked_count,
        overall_status=overall,
        summary=summary,
        checks=checks,
        environment_info=env_info,
    )

    report_file = project_dir / "test_report.json"
    report_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


# ---------------------------------------------------------------------------
# Report retrieval
# ---------------------------------------------------------------------------

def get_latest_test_report(project_id: str) -> TestReport:
    """Retrieves the latest persisted TestReport for a given project."""
    project_dir = get_project_dir(project_id)
    report_file = project_dir / "test_report.json"

    if not report_file.exists():
        raise ReportNotFoundError(
            f"No test report found for project '{project_id}'. Run tests first."
        )
    try:
        return TestReport.model_validate_json(report_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise ReportNotFoundError(f"Failed to read test report: {e}")
