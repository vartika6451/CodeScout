import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.patching.models import FilePatch, Patch, VerificationStatus
from app.patching.verifier import PatchVerifier


class TestPatchVerification(unittest.TestCase):
    """Unit and integration tests for Phase 4 Patch Verification and Regression Detection."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.temp_dir.name)

        # Setup directory structure: app/ and tests/
        (self.repo_dir / "app").mkdir(parents=True, exist_ok=True)
        (self.repo_dir / "tests").mkdir(parents=True, exist_ok=True)

        # app/math_ops.py
        self.math_code = (
            "def divide(a, b):\n"
            "    return a / b\n\n"
            "def multiply(a, b):\n"
            "    return a * b\n"
        )
        (self.repo_dir / "app" / "math_ops.py").write_text(self.math_code)

        # tests/test_math.py with 2 tests:
        # test_divide_zero fails with ZeroDivisionError
        # test_multiply passes
        self.test_code = (
            "import unittest\n"
            "from app.math_ops import divide, multiply\n\n"
            "class TestMath(unittest.TestCase):\n"
            "    def test_divide_zero(self):\n"
            "        self.assertEqual(divide(10, 0), 0)\n\n"
            "    def test_multiply(self):\n"
            "        self.assertEqual(multiply(2, 3), 6)\n"
        )
        (self.repo_dir / "tests" / "test_math.py").write_text(self.test_code)

        self.verifier = PatchVerifier()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_successful_verification_without_regressions(self):
        """Valid patch fixes failing test without introducing regressions -> FIX_VERIFIED."""
        fixed_math_code = (
            "def divide(a, b):\n"
            "    if b == 0:\n"
            "        return 0\n"
            "    return a / b\n\n"
            "def multiply(a, b):\n"
            "    return a * b\n"
        )
        fp = FilePatch(
            file_path="app/math_ops.py",
            original_content=self.math_code,
            proposed_content=fixed_math_code,
            start_line=1,
            end_line=2,
            target_content="def divide(a, b):\n    return a / b",
            replacement="def divide(a, b):\n    if b == 0:\n        return 0\n    return a / b",
        )
        patch = Patch(
            patch_id="P_FIX",
            files_changed=[fp],
            description="Add zero guard",
            reason="Avoid ZeroDivisionError",
        )

        result = self.verifier.verify_patch(
            patch=patch,
            source_repo_path=str(self.repo_dir),
            targeted_test="tests/test_math.py",
        )

        self.assertEqual(result.status, VerificationStatus.FIX_VERIFIED)
        self.assertEqual(len(result.new_regressions), 0)
        self.assertGreater(len(result.fixed_failures), 0)

    def test_02_regression_detection_rejects_patch(self):
        """Patch that fixes target test but breaks multiply() -> PATCH_FAILED (regression)."""
        # Broken patch that corrupts multiply()
        corrupted_code = (
            "def divide(a, b):\n"
            "    return 0\n\n"
            "def multiply(a, b):\n"
            "    return -999\n"  # Breaks test_multiply!
        )
        fp = FilePatch(
            file_path="app/math_ops.py",
            original_content=self.math_code,
            proposed_content=corrupted_code,
        )
        patch = Patch(
            patch_id="P_REGRESS",
            files_changed=[fp],
            description="Bad patch",
            reason="Corrupts multiply",
        )

        result = self.verifier.verify_patch(
            patch=patch,
            source_repo_path=str(self.repo_dir),
            targeted_test="tests/test_math.py",
        )

        # Must NOT be marked FIX_VERIFIED!
        self.assertEqual(result.status, VerificationStatus.PATCH_FAILED)
        self.assertTrue(len(result.new_regressions) > 0)
        self.assertTrue(any("test_multiply" in r for r in result.new_regressions))

    def test_03_pre_existing_failures_handled_separately(self):
        """Pre-existing unrelated failure does not block fix recognition, but is reported."""
        # Add an unrelated pre-existing failing test
        unrelated_test = (
            "import unittest\n"
            "class TestUnrelated(unittest.TestCase):\n"
            "    def test_already_broken(self):\n"
            "        self.assertEqual(1, 999)\n"
        )
        (self.repo_dir / "tests" / "test_unrelated.py").write_text(unrelated_test)

        fixed_math_code = (
            "def divide(a, b):\n"
            "    if b == 0:\n"
            "        return 0\n"
            "    return a / b\n\n"
            "def multiply(a, b):\n"
            "    return a * b\n"
        )
        fp = FilePatch(
            file_path="app/math_ops.py",
            original_content=self.math_code,
            proposed_content=fixed_math_code,
        )
        patch = Patch(
            patch_id="P_PRE",
            files_changed=[fp],
            description="Fix divide",
            reason="Zero division fix",
        )

        result = self.verifier.verify_patch(
            patch=patch,
            source_repo_path=str(self.repo_dir),
            targeted_test="tests/test_math.py",
            run_related_tests=True,
        )

        # Pre-existing failure recognized separately
        self.assertEqual(result.status, VerificationStatus.PRE_EXISTING_FAILURES)
        self.assertTrue(any("test_already_broken" in p for p in result.pre_existing_failures))
        self.assertEqual(len(result.new_regressions), 0)


if __name__ == "__main__":
    unittest.main()
