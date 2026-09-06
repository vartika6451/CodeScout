import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.agents.investigation import (
    BugInvestigationReport,
    bug_investigation_graph,
)
from app.agents.investigation.steps import (
    MAX_TEST_RUNS,
    evaluate_hypotheses,
    execute_test_verification,
    generate_hypotheses,
    generate_report,
    identify_entry_points,
    trace_code,
    understand_bug,
)
from app.agents.tools import clear_graph_cache, run_tests


class TestRuntimeInvestigation(unittest.TestCase):
    """End-to-end integration and hypothesis verification tests for Phase 3 Part 2."""

    def setUp(self):
        clear_graph_cache()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sample_repo = Path(self.temp_dir.name)

        # Create sample buggy repository
        (self.sample_repo / "tests").mkdir(parents=True, exist_ok=True)

        # app.py with controlled TypeError bug
        app_code = (
            "def get_user_profile(user_id):\n"
            "    user = None\n"
            "    return user['name']\n"
        )
        (self.sample_repo / "app.py").write_text(app_code)

        # tests/test_app.py targeting get_user_profile
        test_code = (
            "import unittest\n"
            "from app import get_user_profile\n\n"
            "class TestApp(unittest.TestCase):\n"
            "    def test_get_user_profile(self):\n"
            "        get_user_profile(1)\n"
        )
        (self.sample_repo / "tests" / "test_app.py").write_text(test_code)

    def tearDown(self):
        self.temp_dir.cleanup()
        clear_graph_cache()

    # ==========================================================================
    # 1. Controlled Buggy Repo End-to-End Investigation
    # ==========================================================================
    def test_01_controlled_buggy_repo_investigation(self):
        """
        Tests complete workflow against an isolated buggy repo:
        Bug report -> normalize -> entry point -> hypothesis -> run test in sandbox ->
        capture TypeError -> parse stack trace -> confirm hypothesis -> report.
        """
        initial_state = {
            "bug_report": "TypeError in get_user_profile: 'NoneType' object is not subscriptable",
            "repository": "sample_repo",
            "repo_path": str(self.sample_repo),
        }

        # Run complete graph
        result_state = bug_investigation_graph.invoke(initial_state)

        # 1. Verify test execution occurred in sandbox
        test_runs = result_state.get("test_runs", [])
        self.assertGreaterEqual(len(test_runs), 1)
        first_run = test_runs[0]
        self.assertNotEqual(first_run["exit_code"], 0)
        self.assertEqual(first_run["status"], "failed")

        # 2. Verify deterministic failure parsing captured TypeError
        failures = result_state.get("failures", [])
        self.assertGreaterEqual(len(failures), 1)
        failure = failures[0]
        self.assertEqual(failure["exception_type"], "TypeError")
        self.assertIn("app.py", failure["file_path"])
        self.assertEqual(failure["line_number"], 3)

        # 3. Verify hypotheses evaluation
        hypotheses = result_state.get("hypotheses", [])
        confirmed = result_state.get("confirmed_hypotheses", [])
        rejected = result_state.get("rejected_hypotheses", [])

        self.assertTrue(len(confirmed) > 0, "At least one hypothesis should be confirmed by runtime evidence")
        # Unrelated hypothesis (like database/external failure) should be rejected
        self.assertTrue(len(rejected) > 0, "Unrelated hypotheses should be rejected by runtime evidence")

        # 4. Verify Final Report
        report = result_state.get("final_report", {})
        self.assertIn("likely_root_cause", report)
        self.assertEqual(report["confidence"], "High")
        self.assertGreater(len(report["runtime_evidence"]), 0)
        self.assertGreater(len(report["tests_executed"]), 0)
        self.assertIn("Phase 4", report["recommended_next_step"])

    # ==========================================================================
    # 2. Direct Hypothesis Confirmation & Rejection Logic
    # ==========================================================================
    def test_02_hypothesis_status_transitions(self):
        """
        Verifies that runtime failures update hypothesis status to 'strongly supported'
        and mark contradicting hypotheses as 'rejected'.
        """
        state = {
            "bug_report": "KeyError in auth middleware",
            "repository": "test_repo",
            "repo_path": str(self.sample_repo),
            "step_count": 0,
            "relevant_files": ["app/auth/middleware.py"],
            "hypotheses": [
                {
                    "id": "H1",
                    "title": "Missing Authorization Header",
                    "explanation": "KeyError 'Authorization' raised in auth middleware when parsing headers.",
                    "relevant_files": ["app/auth/middleware.py"],
                    "confidence": 0.5,
                    "status": "inconclusive",
                    "runtime_evidence": [],
                },
                {
                    "id": "H2",
                    "title": "PostgreSQL Database Connection Failure",
                    "explanation": "Database connection timed out or database refused connection.",
                    "relevant_files": ["app/db/connection.py"],
                    "confidence": 0.5,
                    "status": "inconclusive",
                    "runtime_evidence": [],
                },
            ],
            "failures": [
                {
                    "test_name": "tests.test_auth.test_token",
                    "failure_type": "FAIL",
                    "exception_type": "KeyError",
                    "error_message": "'Authorization'",
                    "file_path": "app/auth/middleware.py",
                    "line_number": 31,
                    "is_environment_error": False,
                }
            ],
            "test_runs": [{"status": "failed", "duration": 0.15, "exit_code": 1}],
            "runtime_evidence": [],
        }

        evaluated = evaluate_hypotheses(state)

        h1 = next(h for h in evaluated["hypotheses"] if h["id"] == "H1")
        h2 = next(h for h in evaluated["hypotheses"] if h["id"] == "H2")

        self.assertEqual(h1["status"], "strongly supported")
        self.assertGreaterEqual(h1["confidence"], 0.85)
        self.assertIn("H1", evaluated["confirmed_hypotheses"])

        self.assertEqual(h2["status"], "rejected")
        self.assertLessEqual(h2["confidence"], 0.20)
        self.assertIn("H2", evaluated["rejected_hypotheses"])

    # ==========================================================================
    # 3. Environment Error Does Not Falsely Blame Code
    # ==========================================================================
    def test_03_environment_error_handling(self):
        """
        Verifies that ModuleNotFoundError is classified as an environment setup error,
        leaving hypotheses as 'inconclusive' rather than falsely blaming code.
        """
        state = {
            "bug_report": "Tests fail to run",
            "repository": "test_repo",
            "repo_path": str(self.sample_repo),
            "step_count": 0,
            "hypotheses": [
                {
                    "id": "H1",
                    "title": "App logic broken",
                    "explanation": "Internal application code is corrupted.",
                    "confidence": 0.5,
                    "status": "inconclusive",
                    "runtime_evidence": [],
                }
            ],
            "failures": [
                {
                    "test_name": "environment_setup",
                    "failure_type": "ENVIRONMENT",
                    "exception_type": "ModuleNotFoundError",
                    "error_message": "No module named 'fastapi'",
                    "is_environment_error": True,
                }
            ],
            "test_runs": [{"status": "environment_error", "duration": 0.05, "exit_code": 127}],
            "runtime_evidence": [],
        }

        evaluated = evaluate_hypotheses(state)
        h1 = evaluated["hypotheses"][0]
        self.assertEqual(h1["status"], "inconclusive")
        self.assertIn("environment or dependency setup failure", h1["runtime_evidence"][0])

    # ==========================================================================
    # 4. Safe Investigation on CodeScout Itself
    # ==========================================================================
    def test_04_investigation_on_codescout_itself(self):
        """
        Runs an investigation query against the actual CodeScout backend codebase.
        Verifies safe execution and report generation.
        """
        codescout_backend = str(backend_dir)
        initial_state = {
            "bug_report": "Which tests cover repository code graph analysis?",
            "repository": "CodeScout",
            "repo_path": codescout_backend,
        }

        result = bug_investigation_graph.invoke(initial_state)

        self.assertIn("final_report", result)
        report = result["final_report"]
        self.assertTrue(len(report["relevant_files"]) > 0)
        self.assertIn("confidence", report)
        self.assertIn("likely_root_cause", report)

    # ==========================================================================
    # 5. Maximum Execution Limits
    # ==========================================================================
    def test_05_maximum_execution_limits(self):
        """Verifies that the investigation agent respects MAX_TEST_RUNS and stops."""
        state = {
            "bug_report": "Loop test",
            "repo_path": str(self.sample_repo),
            "test_count": MAX_TEST_RUNS,
            "total_test_runtime": 10.0,
            "test_runs": [{"target": "t1"}, {"target": "t2"}, {"target": "t3"}],
            "step_count": 0,
        }

        res = execute_test_verification(state)
        # Should NOT increment test_count beyond MAX_TEST_RUNS
        self.assertEqual(res["test_count"], MAX_TEST_RUNS)


if __name__ == "__main__":
    unittest.main()
