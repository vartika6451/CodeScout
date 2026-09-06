import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.execution.executor import ExecutionService
from app.execution.models import ExecutionConfig, ExecutionStatus
from app.patching.applier import PatchApplier
from app.patching.models import (
    Patch,
    PatchStatus,
    PatchVerificationResult,
    VerificationStatus,
)
from app.patching.workspace import IsolatedWorkspace

logger = logging.getLogger(__name__)


class PatchVerifier:
    """
    Coordinates multi-level patch verification inside an isolated workspace.
    Reuses Phase 3 execution infrastructure, enforces regression detection,
    and segregates pre-existing failures from new defects.
    """

    def __init__(self, execution_service: Optional[ExecutionService] = None):
        self.service = execution_service or ExecutionService()

    def verify_patch(
        self,
        patch: Patch,
        source_repo_path: str,
        targeted_test: Optional[str] = None,
        run_related_tests: bool = True,
        max_timeout: float = 60.0,
    ) -> PatchVerificationResult:
        """
        Executes multi-level verification of a proposed patch:
        1. Captures baseline test results on original repository.
        2. Applies patch inside an IsolatedWorkspace (source repo untouched).
        3. Level 1: Executes targeted test.
        4. Level 2: Executes related tests to detect regressions.
        5. Compares before/after results to classify outcome.
        """
        config = ExecutionConfig(per_test_timeout=max_timeout)
        resolved_source = str(Path(source_repo_path).resolve())

        # Step 1: Discover candidate tests if targeted_test not provided
        changed_files = [fp.file_path for fp in patch.files_changed]
        if not targeted_test:
            candidates = self.service.find_candidate_tests(
                resolved_source,
                files=changed_files,
            )
            targeted_test = candidates[0] if candidates else None

        # Step 2: Establish baseline results before patch
        baseline_failures: Set[str] = set()
        if targeted_test:
            pre_res = self.service.execute_tests(
                repo_path=resolved_source,
                test_target=targeted_test,
                config=config,
            )
            for f in pre_res.failures:
                baseline_failures.add(f.test_name)

        # Step 3: Create isolated workspace and apply patch
        workspace = IsolatedWorkspace(source_repo_path=resolved_source)
        ws_path = workspace.setup()

        try:
            apply_ok, diff, err_msg = PatchApplier.apply_patch(patch, ws_path)
            if not apply_ok:
                logger.warning(f"Patch verification aborted: application failed: {err_msg}")
                patch.status = PatchStatus.FAILED
                return PatchVerificationResult(
                    patch_id=patch.patch_id,
                    status=VerificationStatus.PATCH_FAILED,
                    diff=diff,
                    iterations_used=patch.iteration,
                )

            # Step 4: Level 1 Verification — Targeted Test Execution
            targeted_result: Optional[Dict[str, Any]] = None
            targeted_passed = False
            post_targeted_failures: Set[str] = set()

            if targeted_test:
                post_run = self.service.execute_tests(
                    repo_path=ws_path,
                    test_target=targeted_test,
                    config=config,
                )
                targeted_result = post_run.to_dict()
                targeted_passed = (post_run.exit_code == 0 and post_run.status == ExecutionStatus.SUCCESS)
                for f in post_run.failures:
                    post_targeted_failures.add(f.test_name)

            # Step 5: Level 2 Verification — Related Tests (Regression Detection)
            related_results: List[Dict[str, Any]] = []
            new_regressions: List[str] = []
            pre_existing: List[str] = []
            fixed: List[str] = []

            # Check fixed failures from targeted test
            for b_fail in baseline_failures:
                if b_fail not in post_targeted_failures:
                    fixed.append(b_fail)
                else:
                    pre_existing.append(b_fail)

            # Any new failure on targeted test?
            for p_fail in post_targeted_failures:
                if p_fail not in baseline_failures:
                    new_regressions.append(p_fail)

            # If targeted test passed and related tests enabled, check other candidates
            if targeted_passed and run_related_tests:
                all_candidates = self.service.find_candidate_tests(
                    ws_path,
                    files=changed_files,
                )
                related_candidates = [c for c in all_candidates if c != targeted_test][:3]

                for rel_target in related_candidates:
                    # Baseline on related target
                    base_rel = self.service.execute_tests(
                        repo_path=resolved_source,
                        test_target=rel_target,
                        config=config,
                    )
                    base_rel_fails = {f.test_name for f in base_rel.failures}

                    # Post-patch on related target
                    post_rel = self.service.execute_tests(
                        repo_path=ws_path,
                        test_target=rel_target,
                        config=config,
                    )
                    related_results.append(post_rel.to_dict())

                    # Check regressions
                    for f in post_rel.failures:
                        if f.test_name not in base_rel_fails:
                            new_regressions.append(f.test_name)
                        else:
                            if f.test_name not in pre_existing:
                                pre_existing.append(f.test_name)

            # Step 6: Determine final verification status
            if new_regressions:
                # Regressions detected: patch broke working functionality!
                status = VerificationStatus.PATCH_FAILED
                patch.status = PatchStatus.FAILED
                logger.warning(f"Patch {patch.patch_id} introduced regressions: {new_regressions}")
            elif targeted_passed:
                if pre_existing:
                    status = VerificationStatus.PRE_EXISTING_FAILURES
                    patch.status = PatchStatus.VERIFIED
                else:
                    status = VerificationStatus.FIX_VERIFIED
                    patch.status = PatchStatus.VERIFIED
            else:
                status = VerificationStatus.PATCH_FAILED
                patch.status = PatchStatus.FAILED

            return PatchVerificationResult(
                patch_id=patch.patch_id,
                status=status,
                targeted_test_result=targeted_result,
                related_test_results=related_results,
                pre_existing_failures=sorted(list(set(pre_existing))),
                fixed_failures=sorted(list(set(fixed))),
                new_regressions=sorted(list(set(new_regressions))),
                diff=patch.diff,
                iterations_used=patch.iteration,
            )

        finally:
            workspace.cleanup()
