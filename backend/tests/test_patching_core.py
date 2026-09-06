import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.patching.applier import PatchApplier
from app.patching.diff import generate_patch_diff, generate_unified_diff
from app.patching.models import FilePatch, Patch, PatchStatus
from app.patching.validator import PatchValidator
from app.patching.workspace import IsolatedWorkspace


class TestPatchingCore(unittest.TestCase):
    """Unit and security tests for Phase 4 Patching Core (Validation, Diffs, Workspaces, Applier)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.temp_dir.name)

        # Create a sample file inside repo
        (self.repo_dir / "app").mkdir(parents=True, exist_ok=True)
        self.sample_file = self.repo_dir / "app" / "auth.py"
        self.initial_code = (
            "def authenticate(headers):\n"
            "    token = headers['Authorization']\n"
            "    return token\n"
        )
        self.sample_file.write_text(self.initial_code, encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    # ==========================================================================
    # 1. Patch Validation & Security Checks
    # ==========================================================================
    def test_01_valid_patch_passes_validation(self):
        """Valid file patch with matching content passes validation."""
        fp = FilePatch(
            file_path="app/auth.py",
            original_content=self.initial_code,
            proposed_content="",
            start_line=2,
            end_line=2,
            target_content="token = headers['Authorization']",
            replacement="token = headers.get('Authorization')",
        )
        patch = Patch(
            patch_id="P1",
            files_changed=[fp],
            description="Fix KeyError",
            reason="Use safe .get()",
        )

        is_valid, err = PatchValidator.validate_patch(patch, str(self.repo_dir))
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_02_validation_rejects_missing_file(self):
        """Patch targeting nonexistent file is rejected."""
        fp = FilePatch(
            file_path="app/nonexistent.py",
            original_content="",
            proposed_content="print(1)",
        )
        patch = Patch(patch_id="P2", files_changed=[fp], description="", reason="")

        is_valid, err = PatchValidator.validate_patch(patch, str(self.repo_dir))
        self.assertFalse(is_valid)
        self.assertIn("does not exist", err)

    def test_03_security_rejects_path_traversal(self):
        """Security: Rejects path traversal and absolute paths."""
        bad_paths = [
            "../../etc/passwd",
            "/etc/shadow",
            "app/../../secret.py",
        ]
        for bad_p in bad_paths:
            fp = FilePatch(
                file_path=bad_p,
                original_content="",
                proposed_content="hack",
            )
            patch = Patch(patch_id="P_BAD", files_changed=[fp], description="", reason="")
            is_valid, err = PatchValidator.validate_patch(patch, str(self.repo_dir))
            self.assertFalse(is_valid)
            self.assertTrue("Path traversal" in err or "escapes workspace" in err)

    def test_04_validation_rejects_stale_original_content(self):
        """Integrity: Rejects patch if file content has changed since generation (no blind overwrite)."""
        fp = FilePatch(
            file_path="app/auth.py",
            original_content="def authenticate(headers):\n    token = 'CHANGED'\n",
            proposed_content="def authenticate(headers):\n    token = None\n",
        )
        patch = Patch(patch_id="P_STALE", files_changed=[fp], description="", reason="")

        is_valid, err = PatchValidator.validate_patch(patch, str(self.repo_dir))
        self.assertFalse(is_valid)
        self.assertIn("changed since patch generation", err)

    def test_05_validation_rejects_invalid_line_range(self):
        """Validation: Rejects invalid line ranges (start > end or start < 1)."""
        fp = FilePatch(
            file_path="app/auth.py",
            original_content=self.initial_code,
            proposed_content="",
            start_line=10,
            end_line=2,
            replacement="pass",
        )
        patch = Patch(patch_id="P_LINE", files_changed=[fp], description="", reason="")

        is_valid, err = PatchValidator.validate_patch(patch, str(self.repo_dir))
        self.assertFalse(is_valid)
        self.assertIn("cannot be less than", err)

    # ==========================================================================
    # 2. Unified Diff Generation
    # ==========================================================================
    def test_06_unified_diff_format(self):
        """Unified diff produces valid Git-style headers and precise changes."""
        orig = "def foo():\n    return 1\n"
        prop = "def foo():\n    return 2\n"
        diff = generate_unified_diff(orig, prop, "foo.py")

        self.assertIn("--- a/foo.py", diff)
        self.assertIn("+++ b/foo.py", diff)
        self.assertIn("-    return 1", diff)
        self.assertIn("+    return 2", diff)

    # ==========================================================================
    # 3. Isolated Workspace & Safety
    # ==========================================================================
    def test_07_isolated_workspace_preserves_source_repository(self):
        """Modifying files inside an isolated workspace leaves the original source repo untouched."""
        with IsolatedWorkspace(str(self.repo_dir)) as ws_path:
            ws_file = Path(ws_path) / "app" / "auth.py"
            # Overwrite inside isolated workspace
            ws_file.write_text("# MODIFIED IN WORKSPACE", encoding="utf-8")
            self.assertEqual(ws_file.read_text(), "# MODIFIED IN WORKSPACE")

        # Original source repository MUST remain completely untouched!
        self.assertEqual(self.sample_file.read_text(), self.initial_code)

    def test_08_workspace_reset(self):
        """Workspace reset discards modifications and restores baseline cleanly."""
        ws = IsolatedWorkspace(str(self.repo_dir))
        ws_path = ws.setup()

        try:
            ws_file = Path(ws_path) / "app" / "auth.py"
            ws_file.write_text("# CORRUPTED CODE", encoding="utf-8")
            self.assertIn("CORRUPTED", ws_file.read_text())

            # Reset workspace
            ws.reset()
            self.assertEqual(ws_file.read_text(), self.initial_code)
        finally:
            ws.cleanup()

    # ==========================================================================
    # 4. Patch Application & Revert
    # ==========================================================================
    def test_09_patch_application_and_revert(self):
        """PatchApplier applies surgical edits and can revert back to original content."""
        with IsolatedWorkspace(str(self.repo_dir)) as ws_path:
            fp = FilePatch(
                file_path="app/auth.py",
                original_content=self.initial_code,
                proposed_content="",
                start_line=2,
                end_line=2,
                target_content="token = headers['Authorization']",
                replacement="    token = headers.get('Authorization')",
            )
            patch = Patch(
                patch_id="P_APP",
                files_changed=[fp],
                description="Use get",
                reason="Prevent KeyError",
            )

            ok, diff, err = PatchApplier.apply_patch(patch, ws_path)
            self.assertTrue(ok)
            self.assertIn("+    token = headers.get('Authorization')", diff)

            # Verify file modified in workspace
            ws_file = Path(ws_path) / "app" / "auth.py"
            self.assertIn("headers.get('Authorization')", ws_file.read_text())

            # Revert patch
            revert_ok = PatchApplier.revert_patch(patch, ws_path)
            self.assertTrue(revert_ok)
            self.assertEqual(ws_file.read_text(), self.initial_code)


if __name__ == "__main__":
    unittest.main()
