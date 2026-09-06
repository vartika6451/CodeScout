import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.execution.detector import FrameworkDetector
from app.execution.executor import ExecutionService
from app.execution.models import (
    ExecutionConfig,
    ExecutionResult,
    ExecutionStatus,
    ParsedFailure,
)
from app.execution.parser import FailureParser
from app.execution.sandbox import SubprocessSandbox


class TestExecutionSandbox(unittest.TestCase):
    """Unit and security tests for Phase 3 Part 2 Execution Layer."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = self.temp_dir.name
        self.service = ExecutionService()

    def tearDown(self):
        self.temp_dir.cleanup()

    # ==========================================================================
    # 1. Execution Result & Status Verification
    # ==========================================================================
    def test_01_successful_test_execution(self):
        """Test successful execution returns exit_code=0 and SUCCESS status."""
        test_file = Path(self.repo_path) / "test_success.py"
        test_file.write_text(
            "import unittest\n"
            "class TestSample(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertEqual(1 + 1, 2)\n"
        )

        result = self.service.execute_tests(
            repo_path=self.repo_path,
            test_target="test_success.py",
        )

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertFalse(result.timed_out)
        self.assertFalse(result.truncated_output)
        self.assertGreater(result.duration, 0.0)
        self.assertEqual(len(result.failures), 0)

    def test_02_failed_test_execution(self):
        """Test failed execution returns exit_code!=0, FAILED status, and parsed failure."""
        test_file = Path(self.repo_path) / "test_fail.py"
        test_file.write_text(
            "import unittest\n"
            "class TestSample(unittest.TestCase):\n"
            "    def test_assertion(self):\n"
            "        self.assertEqual(1, 2)\n"
        )

        result = self.service.execute_tests(
            repo_path=self.repo_path,
            test_target="test_fail.py",
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertFalse(result.timed_out)
        self.assertGreaterEqual(len(result.failures), 1)

        f = result.failures[0]
        self.assertIn("test_assertion", f.test_name)
        self.assertEqual(f.exception_type, "AssertionError")

    # ==========================================================================
    # 2. Timeout Enforcement
    # ==========================================================================
    def test_03_timeout_handling(self):
        """Test that long-running or hanging tests are terminated when exceeding per_test_timeout."""
        test_file = Path(self.repo_path) / "test_sleep.py"
        test_file.write_text(
            "import unittest, time\n"
            "class TestHangs(unittest.TestCase):\n"
            "    def test_sleep(self):\n"
            "        time.sleep(10)\n"
        )

        config = ExecutionConfig(per_test_timeout=1.0)
        result = self.service.execute_tests(
            repo_path=self.repo_path,
            test_target="test_sleep.py",
            config=config,
        )

        self.assertTrue(result.timed_out)
        self.assertEqual(result.status, ExecutionStatus.TIMEOUT)
        self.assertIn("timed out", result.error_summary.lower())

    # ==========================================================================
    # 3. Output Truncation
    # ==========================================================================
    def test_04_output_truncation(self):
        """Test that excessive output is truncated at max_output_size."""
        test_file = Path(self.repo_path) / "test_spam.py"
        test_file.write_text(
            "import unittest\n"
            "class TestSpam(unittest.TestCase):\n"
            "    def test_print(self):\n"
            "        for _ in range(5000):\n"
            "            print('A' * 200)\n"
        )

        config = ExecutionConfig(max_output_size=4096)  # 4 KB limit
        result = self.service.execute_tests(
            repo_path=self.repo_path,
            test_target="test_spam.py",
            config=config,
        )

        self.assertTrue(result.truncated_output)
        self.assertIn("[Output truncated at 4 KB limit]", result.stdout)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 5000)

    # ==========================================================================
    # 4. Security Tests (Path Traversal, Injection, Host Secrets)
    # ==========================================================================
    def test_05_security_reject_path_traversal(self):
        """Security: Rejects path traversal targets containing '../'."""
        malicious_targets = [
            "../../etc/passwd",
            "../other_dir/test.py",
            "/etc/shadow",
            "tests/../../secret.py",
        ]
        for target in malicious_targets:
            result = self.service.execute_tests(
                repo_path=self.repo_path,
                test_target=target,
            )
            self.assertEqual(
                result.status,
                ExecutionStatus.SECURITY_VIOLATION,
                f"Target should have been rejected: {target}",
            )
            self.assertEqual(result.exit_code, 126)

    def test_06_security_reject_command_injection(self):
        """Security: Rejects shell metacharacters and command-chaining payloads."""
        malicious_commands = [
            "tests/test_auth.py; rm -rf /",
            "test.py && cat /etc/passwd",
            "test.py | sh",
            "`id`",
            "$(whoami)",
            "test.py > output.txt",
            "test.py\nrm -rf .",
        ]
        for payload in malicious_commands:
            result = self.service.execute_tests(
                repo_path=self.repo_path,
                test_target=payload,
            )
            self.assertEqual(
                result.status,
                ExecutionStatus.SECURITY_VIOLATION,
                f"Payload should have been rejected: {payload}",
            )

    def test_07_security_host_secret_isolation(self):
        """Security: Verifies host environment secrets (e.g. GEMINI_API_KEY, DATABASE_URL) are NOT leaked."""
        os.environ["GEMINI_API_KEY"] = "super-secret-gemini-key-12345"
        os.environ["DATABASE_URL"] = "postgres://root:password@localhost:5432/db"

        test_file = Path(self.repo_path) / "test_env.py"
        test_file.write_text(
            "import os, unittest\n"
            "class TestEnv(unittest.TestCase):\n"
            "    def test_no_secrets(self):\n"
            "        # Neither secret should be present in the sandbox environment\n"
            "        self.assertNotIn('GEMINI_API_KEY', os.environ)\n"
            "        self.assertNotIn('DATABASE_URL', os.environ)\n"
        )

        result = self.service.execute_tests(
            repo_path=self.repo_path,
            test_target="test_env.py",
        )

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)

    # ==========================================================================
    # 5. Deterministic Failure & Traceback Parser
    # ==========================================================================
    def test_08_parse_pytest_traceback(self):
        """Test deterministic parsing of pytest failure traceback."""
        sample_pytest_output = (
            "============================= test session starts ==============================\n"
            "collected 1 item\n\n"
            "tests/test_auth.py F                                                     [100%]\n\n"
            "=================================== FAILURES ===================================\n"
            "__________________________ test_login_without_token ___________________________\n\n"
            "    def test_login_without_token():\n"
            ">       resp = login_user({})\n\n"
            "tests/test_auth.py:18: in test_login_without_token\n"
            "    resp = login_user({})\n"
            "app/auth/service.py:42: in login_user\n"
            "    token = headers['Authorization']\n"
            "E   KeyError: 'Authorization'\n"
            "=========================== short test summary info ============================\n"
            "FAILED tests/test_auth.py::test_login_without_token - KeyError: 'Authorization'\n"
            "============================== 1 failed in 0.12s ==============================="
        )

        failures = FailureParser.parse_output(
            stdout=sample_pytest_output,
            stderr="",
            test_framework="pytest",
        )

        self.assertEqual(len(failures), 1)
        f = failures[0]
        self.assertIn("test_login_without_token", f.test_name)
        self.assertEqual(f.exception_type, "KeyError")
        self.assertEqual(f.error_message, "'Authorization'")
        self.assertIn("app/auth/service.py", f.file_path)
        self.assertEqual(f.line_number, 42)

    def test_09_parse_environment_error(self):
        """Test that ModuleNotFoundError is classified as an environment setup error, not application failure."""
        sample_env_err = (
            "Traceback (most recent call last):\n"
            "  File \"tests/test_auth.py\", line 2, in <module>\n"
            "    import nonexistent_package\n"
            "ModuleNotFoundError: No module named 'nonexistent_package'\n"
        )

        failures = FailureParser.parse_output(
            stdout="",
            stderr=sample_env_err,
        )

        self.assertEqual(len(failures), 1)
        f = failures[0]
        self.assertTrue(f.is_environment_error)
        self.assertEqual(f.exception_type, "ModuleNotFoundError")
        self.assertEqual(f.failure_type, "ENVIRONMENT")

    # ==========================================================================
    # 6. Test Framework Detection
    # ==========================================================================
    def test_10_framework_detection(self):
        """Test detection of pytest and unittest configuration files."""
        # Unittest default when empty
        fw, ok = FrameworkDetector.detect_framework(self.repo_path)
        self.assertIn(fw, ("unittest", "pytest"))

        # Explicit pytest.ini
        (Path(self.repo_path) / "pytest.ini").write_text("[pytest]\n")
        fw, _ = FrameworkDetector.detect_framework(self.repo_path)
        self.assertEqual(fw, "pytest")


if __name__ == "__main__":
    unittest.main()
