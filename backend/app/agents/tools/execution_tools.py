import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from app.execution.executor import ExecutionService
from app.execution.models import ExecutionConfig, ExecutionStatus

logger = logging.getLogger(__name__)

_EXECUTION_SERVICE: Optional[ExecutionService] = None


def get_execution_service() -> ExecutionService:
    """Returns a singleton or initialized ExecutionService instance."""
    global _EXECUTION_SERVICE
    if _EXECUTION_SERVICE is None:
        _EXECUTION_SERVICE = ExecutionService()
    return _EXECUTION_SERVICE


def run_tests(
    test_target: Optional[str] = None,
    repo_path: Optional[Union[str, Path]] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Executes repository tests safely inside an isolated execution sandbox.
    Prevents arbitrary shell execution, enforces resource limits, timeouts, and output limits,
    and returns deterministically parsed failure and stack trace data.

    Args:
        test_target: Optional path to a specific test file or test node
                     (e.g., 'tests/test_auth.py' or 'tests/test_auth.py::test_login').
                     If None, runs the repository's configured test suite.
        repo_path: Path to the target repository. Defaults to the backend/workspace directory.
        timeout: Maximum execution time in seconds (default: 60.0).

    Returns:
        Structured dictionary with exit code, stdout, stderr, parsed failures, and runtime evidence summary.
    """
    if repo_path is None:
        current_dir = Path(__file__).resolve().parent.parent.parent
        repo_path = current_dir if current_dir.name == "backend" else current_dir.parent

    resolved_path = str(Path(repo_path).resolve())
    service = get_execution_service()
    config = ExecutionConfig(per_test_timeout=timeout)

    result = service.execute_tests(
        repo_path=resolved_path,
        test_target=test_target,
        config=config,
    )

    # Build human-readable runtime evidence summary for agent reasoning
    runtime_summary_lines = []
    if result.status == ExecutionStatus.SUCCESS:
        runtime_summary_lines.append(f"All tests passed successfully ({result.duration}s).")
    elif result.status == ExecutionStatus.TIMEOUT:
        runtime_summary_lines.append(f"Test execution timed out after {timeout} seconds.")
    elif result.status == ExecutionStatus.SECURITY_VIOLATION:
        runtime_summary_lines.append(f"Security violation: {result.error_summary}")
    elif result.status == ExecutionStatus.ENVIRONMENT_ERROR:
        runtime_summary_lines.append(f"Environment/setup error: {result.error_summary or 'Missing dependency'}")
    else:
        runtime_summary_lines.append(f"Test execution failed (exit code {result.exit_code}, {result.duration}s).")
        for f in result.failures:
            loc_str = f" at {f.file_path}:{f.line_number}" if f.file_path else ""
            runtime_summary_lines.append(
                f"- Test: {f.test_name} | Exception: {f.exception_type}: {f.error_message}{loc_str}"
            )

    return {
        "success": result.exit_code == 0,
        "tool": "run_tests",
        "target": test_target,
        "command": result.command,
        "exit_code": result.exit_code,
        "status": result.status.value,
        "duration": result.duration,
        "timed_out": result.timed_out,
        "truncated_output": result.truncated_output,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "failures": [f.to_dict() for f in result.failures],
        "failure_count": len(result.failures),
        "error_summary": result.error_summary,
        "runtime_evidence_summary": "\n".join(runtime_summary_lines),
    }
