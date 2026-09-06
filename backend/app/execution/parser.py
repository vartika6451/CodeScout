import re
from pathlib import Path
from typing import List, Optional

from app.execution.models import ParsedFailure


class FailureParser:
    """
    Deterministically parses pytest and unittest execution output to extract
    structured test failure, error, and traceback information.
    """

    # Matches exception line: "E   KeyError: 'Authorization'" or "TypeError: 'NoneType' object is not subscriptable"
    EXCEPTION_PATTERN = re.compile(
        r"^(?:E\s+)?([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception|AssertionError|KeyError|TypeError|ValueError|AttributeError|ZeroDivisionError|IndexError):\s*(.*)$",
        re.MULTILINE,
    )

    # Matches file and line in traceback:
    # "  File \"/path/to/app.py\", line 42, in some_func"
    # or pytest style: "app/routes/login.py:20: in login"
    TRACEBACK_FRAME_UNITTEST = re.compile(
        r'File\s+["\']([^"\']+)["\'],\s+line\s+(\d+)(?:,\s+in\s+([A-Za-z0-9_]+))?',
        re.IGNORECASE,
    )
    TRACEBACK_FRAME_PYTEST = re.compile(
        r"^([A-Za-z0-9_\-/\\]+\.py):(\d+):\s+in\s+([A-Za-z0-9_]+)",
        re.MULTILINE,
    )

    # Matches pytest failure header: "FAILED tests/test_login.py::test_login_without_token"
    PYTEST_FAILED_HEADER = re.compile(
        r"(?:FAILED|ERROR)\s+([A-Za-z0-9_\-/\\]+\.py::[A-Za-z0-9_]+)",
        re.IGNORECASE,
    )

    # Matches unittest failure header: "FAIL: test_login (tests.test_login.TestLogin)"
    UNITTEST_FAILED_HEADER = re.compile(
        r"(?:FAIL|ERROR):\s+([A-Za-z0-9_]+)\s+\(([^)]+)\)",
        re.IGNORECASE,
    )

    @classmethod
    def parse_output(
        cls,
        stdout: str,
        stderr: str,
        repo_path: Optional[str] = None,
        test_framework: Optional[str] = None,
    ) -> List[ParsedFailure]:
        """
        Extracts structured ParsedFailure objects from combined stdout and stderr.
        """
        combined = (stdout or "") + "\n" + (stderr or "")
        failures: List[ParsedFailure] = []

        if not combined.strip():
            return failures

        # 1. Check for global environment / dependency error first
        if "ModuleNotFoundError:" in combined or "ImportError:" in combined:
            env_match = cls.EXCEPTION_PATTERN.search(combined)
            exc_type = env_match.group(1) if env_match else "ModuleNotFoundError"
            msg = env_match.group(2) if env_match else "Required dependency not found in environment."
            failures.append(
                ParsedFailure(
                    test_name="environment_setup",
                    failure_type="ENVIRONMENT",
                    exception_type=exc_type,
                    error_message=msg,
                    is_environment_error=True,
                )
            )
            return failures

        # 2. Try parsing Pytest output
        if test_framework == "pytest" or "=== FAILURES ===" in combined or "FAILED " in combined:
            pytest_failures = cls._parse_pytest(combined, repo_path)
            if pytest_failures:
                return pytest_failures

        # 3. Try parsing Unittest output
        unittest_failures = cls._parse_unittest(combined, repo_path)
        if unittest_failures:
            return unittest_failures

        # 4. Fallback: generic traceback parsing if standard headers weren't found
        fallback = cls._parse_generic_traceback(combined, repo_path)
        if fallback:
            return [fallback]

        return failures

    @classmethod
    def _parse_pytest(cls, text: str, repo_path: Optional[str] = None) -> List[ParsedFailure]:
        failures: List[ParsedFailure] = []

        # Split into blocks based on failure headers
        sections = re.split(r"_{3,}\s+([A-Za-z0-9_\[\]\-]+)\s+_{3,}", text)
        if len(sections) > 1:
            for i in range(1, len(sections), 2):
                test_name = sections[i]
                body = sections[i + 1] if i + 1 < len(sections) else ""
                failure = cls._extract_failure_from_block(test_name, body, repo_path)
                if failure:
                    failures.append(failure)
            if failures:
                return failures

        # If sections splitting did not produce failures, check short summary lines
        summary_matches = cls.PYTEST_FAILED_HEADER.findall(text)
        for target in summary_matches:
            # Look for exception in the whole text
            exc_match = cls.EXCEPTION_PATTERN.search(text)
            exc_type = exc_match.group(1) if exc_match else "AssertionError"
            msg = exc_match.group(2) if exc_match else "Test failed"
            loc = cls._find_most_relevant_location(text, repo_path)

            failures.append(
                ParsedFailure(
                    test_name=target,
                    failure_type="FAIL",
                    exception_type=exc_type,
                    error_message=msg,
                    file_path=loc[0],
                    line_number=loc[1],
                    stack_trace=cls._extract_frames(text, repo_path),
                )
            )

        return failures

    @classmethod
    def _parse_unittest(cls, text: str, repo_path: Optional[str] = None) -> List[ParsedFailure]:
        failures: List[ParsedFailure] = []

        # Unittest separates tests with "=" * 70
        blocks = re.split(r"={40,}", text)
        for block in blocks:
            header_match = cls.UNITTEST_FAILED_HEADER.search(block)
            if header_match:
                test_func = header_match.group(1)
                test_class = header_match.group(2)
                test_name = f"{test_class}.{test_func}"

                failure = cls._extract_failure_from_block(test_name, block, repo_path)
                if failure:
                    failures.append(failure)

        return failures

    @classmethod
    def _extract_failure_from_block(
        cls, test_name: str, block: str, repo_path: Optional[str] = None
    ) -> Optional[ParsedFailure]:
        exc_match = cls.EXCEPTION_PATTERN.search(block)
        exc_type = exc_match.group(1) if exc_match else "Failure"
        msg = exc_match.group(2) if exc_match else ""

        loc = cls._find_most_relevant_location(block, repo_path)
        frames = cls._extract_frames(block, repo_path)

        is_env = exc_type in ("ModuleNotFoundError", "ImportError")

        return ParsedFailure(
            test_name=test_name,
            failure_type="ENVIRONMENT" if is_env else "FAIL",
            exception_type=exc_type,
            error_message=msg.strip(),
            file_path=loc[0],
            line_number=loc[1],
            stack_trace=frames,
            is_environment_error=is_env,
        )

    @classmethod
    def _parse_generic_traceback(cls, text: str, repo_path: Optional[str] = None) -> Optional[ParsedFailure]:
        if "Traceback (most recent call last):" not in text:
            return None

        exc_match = cls.EXCEPTION_PATTERN.search(text)
        if not exc_match:
            return None

        exc_type = exc_match.group(1)
        msg = exc_match.group(2)
        loc = cls._find_most_relevant_location(text, repo_path)
        frames = cls._extract_frames(text, repo_path)
        is_env = exc_type in ("ModuleNotFoundError", "ImportError")

        return ParsedFailure(
            test_name="execution_traceback",
            failure_type="ENVIRONMENT" if is_env else "ERROR",
            exception_type=exc_type,
            error_message=msg.strip(),
            file_path=loc[0],
            line_number=loc[1],
            stack_trace=frames,
            is_environment_error=is_env,
        )

    @classmethod
    def _find_most_relevant_location(
        cls, text: str, repo_path: Optional[str] = None
    ) -> tuple[Optional[str], Optional[int]]:
        """
        Picks the most informative file and line in the stack trace.
        Prefers non-test application files over test files, and always relative to repo_path.
        """
        frames_unittest = cls.TRACEBACK_FRAME_UNITTEST.findall(text)
        frames_pytest = cls.TRACEBACK_FRAME_PYTEST.findall(text)

        all_frames = []
        for fp, line, func in frames_unittest:
            all_frames.append((fp, int(line), func))
        for fp, line, func in frames_pytest:
            all_frames.append((fp, int(line), func))

        if not all_frames:
            return None, None

        # Clean file paths relative to repo_path if provided
        cleaned = []
        for fp, line, func in all_frames:
            rel = cls._make_relative(fp, repo_path)
            cleaned.append((rel, line, func))

        # Prioritize application files (e.g. not starting with test_)
        app_frames = [
            (fp, line)
            for fp, line, _ in cleaned
            if not Path(fp).name.startswith("test_") and "site-packages" not in fp
        ]

        if app_frames:
            return app_frames[-1]  # The deepest application call

        # Fallback to last frame in trace
        return cleaned[-1][0], cleaned[-1][1]

    @classmethod
    def _extract_frames(cls, text: str, repo_path: Optional[str] = None) -> List[str]:
        frames = []
        for match in cls.TRACEBACK_FRAME_UNITTEST.finditer(text):
            fp = cls._make_relative(match.group(1), repo_path)
            line = match.group(2)
            func = match.group(3) or "unknown"
            frames.append(f"{fp}:{line} in {func}")

        for match in cls.TRACEBACK_FRAME_PYTEST.finditer(text):
            fp = cls._make_relative(match.group(1), repo_path)
            line = match.group(2)
            func = match.group(3) or "unknown"
            frames.append(f"{fp}:{line} in {func}")

        return frames

    @staticmethod
    def _make_relative(file_path: str, repo_path: Optional[str] = None) -> str:
        if not repo_path:
            return file_path
        try:
            return str(Path(file_path).resolve().relative_to(Path(repo_path).resolve()))
        except Exception:
            return file_path
