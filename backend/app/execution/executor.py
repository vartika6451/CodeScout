import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from app.execution.detector import FrameworkDetector
from app.execution.models import (
    ExecutionConfig,
    ExecutionResult,
    ExecutionStatus,
)
from app.execution.parser import FailureParser
from app.execution.sandbox import BaseSandbox, DockerSandbox, SubprocessSandbox

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    Central orchestration service for safe repository test execution.
    Combines framework detection, target validation, sandbox isolation, and failure parsing.
    """

    def __init__(
        self,
        sandbox: Optional[BaseSandbox] = None,
        default_config: Optional[ExecutionConfig] = None,
    ):
        # Default to SubprocessSandbox (or DockerSandbox if Docker daemon is active)
        if sandbox:
            self.sandbox = sandbox
        elif DockerSandbox.is_docker_available():
            self.sandbox = DockerSandbox()
        else:
            self.sandbox = SubprocessSandbox()

        self.config = default_config or ExecutionConfig()

    def execute_tests(
        self,
        repo_path: str,
        test_target: Optional[str] = None,
        config: Optional[ExecutionConfig] = None,
    ) -> ExecutionResult:
        """
        Safely executes repository tests under sandbox isolation.

        Steps:
        1. Validate target path against security rules.
        2. Detect repository test framework (pytest vs unittest).
        3. Build argument vector for test execution.
        4. Execute inside sandbox with resource, timeout, and environment limits.
        5. Deterministically parse test failures and stack traces.
        """
        cfg = config or self.config
        resolved_repo = str(Path(repo_path).resolve())

        # 1. Security Check: Validate test target
        is_valid, err_msg = SubprocessSandbox.validate_target(test_target, resolved_repo)
        if not is_valid:
            logger.warning(f"Security violation detected in test target: {err_msg}")
            return ExecutionResult(
                command=f"run_tests target={test_target!r}",
                exit_code=126,
                stdout="",
                stderr=f"Security violation: {err_msg}",
                timed_out=False,
                duration=0.0,
                working_directory=resolved_repo,
                status=ExecutionStatus.SECURITY_VIOLATION,
                error_summary=err_msg,
            )

        # 2. Detect test framework
        framework, is_available = FrameworkDetector.detect_framework(
            resolved_repo, python_bin=cfg.python_binary
        )

        if not is_available:
            logger.warning(f"Detected framework '{framework}' is not installed in the environment.")
            return ExecutionResult(
                command=f"python -m {framework}",
                exit_code=127,
                stdout="",
                stderr=f"Test runner '{framework}' is configured in the repository but not installed in the execution environment.",
                timed_out=False,
                duration=0.0,
                working_directory=resolved_repo,
                test_framework=framework,
                status=ExecutionStatus.ENVIRONMENT_ERROR,
                error_summary=f"Environment error: Test framework '{framework}' missing.",
            )

        # 3. Build command argument vector
        cmd = FrameworkDetector.build_test_command(
            framework=framework,
            repo_path=resolved_repo,
            target=test_target,
            python_bin=cfg.python_binary,
        )

        # 4. Execute inside Sandbox
        result = self.sandbox.execute(
            command=cmd,
            working_directory=resolved_repo,
            config=cfg,
            framework=framework,
        )

        # 5. Parse test failures deterministically
        failures = FailureParser.parse_output(
            stdout=result.stdout,
            stderr=result.stderr,
            repo_path=resolved_repo,
            test_framework=framework,
        )
        result.failures = failures

        # If failures indicate environment errors, update status
        if any(f.is_environment_error for f in failures):
            result.status = ExecutionStatus.ENVIRONMENT_ERROR

        return result

    def find_candidate_tests(
        self,
        repo_path: str,
        symbols: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
    ) -> List[str]:
        """Discovers candidate test files prioritized by relevance to suspect symbols/files."""
        return FrameworkDetector.find_candidate_tests(repo_path, symbols=symbols, files=files)
