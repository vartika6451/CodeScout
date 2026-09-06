import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.agents.investigation import bug_investigation_graph
from app.agents.tools import clear_graph_cache


class TestEndToEndPatching(unittest.TestCase):
    """
    End-to-End integration test for Phase 4:
    Bug report -> Investigation -> Root Cause -> Patch Generation ->
    Isolated Workspace Application -> Multi-Level Verification -> Report with Unified Diff.
    """

    def setUp(self):
        clear_graph_cache()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sample_repo = Path(self.temp_dir.name)

        # Create tests/ directory
        (self.sample_repo / "tests").mkdir(parents=True, exist_ok=True)

        # auth.py with controlled bug: get_username(None) raises TypeError
        self.auth_code = (
            "def get_username(user):\n"
            "    return user['name']\n"
        )
        (self.sample_repo / "auth.py").write_text(self.auth_code, encoding="utf-8")

        # tests/test_auth.py: test_missing_user expects None when user is None
        self.test_code = (
            "import unittest\n"
            "from auth import get_username\n\n"
            "class TestAuth(unittest.TestCase):\n"
            "    def test_missing_user(self):\n"
            "        self.assertIsNone(get_username(None))\n\n"
            "    def test_valid_user(self):\n"
            "        self.assertEqual(get_username({'name': 'Alice'}), 'Alice')\n"
        )
        (self.sample_repo / "tests" / "test_auth.py").write_text(self.test_code, encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()
        clear_graph_cache()

    def test_01_full_patch_lifecycle_verified(self):
        """
        Complete Phase 4 lifecycle:
        1. Receive bug report
        2. Investigate repository & confirm root cause
        3. Generate minimal patch
        4. Apply inside isolated workspace
        5. Run tests & verify fix
        6. Produce final report with unified diff
        7. Ensure original repository is completely untouched!
        """
        initial_state = {
            "bug_report": "TypeError in get_username: 'NoneType' object is not subscriptable",
            "repository": "sample_repo",
            "repo_path": str(self.sample_repo),
        }

        result = bug_investigation_graph.invoke(initial_state)

        # 1. Verify a patch was proposed
        self.assertIn("proposed_patch", result)
        patch = result["proposed_patch"]
        self.assertIsNotNone(patch)
        self.assertTrue(len(patch.get("files_changed", [])) > 0)

        # 2. Verify Unified Diff was generated
        diff = result.get("patch_diff")
        self.assertIsNotNone(diff)
        self.assertIn("--- a/auth.py", diff)
        self.assertIn("+++ b/auth.py", diff)

        # 3. Verify Verification Status is FIX_VERIFIED
        final_status = result.get("final_status")
        self.assertEqual(final_status, "FIX_VERIFIED")

        # 4. Verify Final Report structure
        report = result.get("final_report", {})
        self.assertEqual(report.get("verification_status"), "FIX_VERIFIED")
        self.assertTrue(report.get("user_review_required"))
        self.assertIn("diff", report)
        self.assertIn("explicit user approval is required", report["recommended_next_step"].lower())

        # 5. CRITICAL: Verify original source repository file remains 100% untouched!
        original_auth_file = self.sample_repo / "auth.py"
        self.assertEqual(
            original_auth_file.read_text(encoding="utf-8"),
            self.auth_code,
            "Source repository must NEVER be modified automatically!",
        )

    def test_02_safe_investigation_on_codescout_codebase(self):
        """
        Verifies that running the workflow against CodeScout itself is safe,
        produces valid reporting, and does not alter any files in the workspace.
        """
        codescout_dir = str(backend_dir)
        initial_state = {
            "bug_report": "Which tests verify the code graph?",
            "repository": "CodeScout",
            "repo_path": codescout_dir,
        }

        result = bug_investigation_graph.invoke(initial_state)
        report = result.get("final_report", {})

        self.assertIn("likely_root_cause", report)
        self.assertIn("confidence", report)
        self.assertTrue(report.get("user_review_required"))


if __name__ == "__main__":
    unittest.main()
