import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.patching.generator import PatchGenerator
from app.patching.models import Patch
from app.patching.verifier import PatchVerifier

logger = logging.getLogger(__name__)

_VERIFIER: Optional[PatchVerifier] = None


def get_patch_verifier() -> PatchVerifier:
    global _VERIFIER
    if _VERIFIER is None:
        _VERIFIER = PatchVerifier()
    return _VERIFIER


def propose_patch(
    bug_report: str,
    root_cause: str,
    repo_path: Optional[Union[str, Path]] = None,
    failures: Optional[List[Dict[str, Any]]] = None,
    relevant_files: Optional[List[str]] = None,
    iteration: int = 1,
    previous_attempts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generates a structured, minimal code patch targeting the confirmed root cause.

    Returns:
        Structured dictionary containing the proposed patch metadata and unified diff.
    """
    if repo_path is None:
        current_dir = Path(__file__).resolve().parent.parent.parent
        repo_path = current_dir if current_dir.name == "backend" else current_dir.parent

    resolved_path = str(Path(repo_path).resolve())
    patch = PatchGenerator.generate_patch(
        bug_report=bug_report,
        root_cause=root_cause,
        repo_path=resolved_path,
        failures=failures,
        relevant_files=relevant_files,
        iteration=iteration,
        previous_attempts=previous_attempts,
    )

    if not patch:
        return {
            "success": False,
            "tool": "propose_patch",
            "error": "Failed to synthesize patch for the identified failure point.",
        }

    return {
        "success": True,
        "tool": "propose_patch",
        "patch": patch.to_dict(),
        "diff": patch.diff,
        "description": patch.description,
        "files_changed": [fp.file_path for fp in patch.files_changed],
    }


def apply_and_verify_patch(
    patch_dict: Dict[str, Any],
    repo_path: Optional[Union[str, Path]] = None,
    targeted_test: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Safely applies a proposed patch inside an isolated workspace and runs multi-level
    test verification with regression detection. The original repository is untouched.

    Returns:
        Structured dictionary containing verification status, fixed failures, and regressions.
    """
    if repo_path is None:
        current_dir = Path(__file__).resolve().parent.parent.parent
        repo_path = current_dir if current_dir.name == "backend" else current_dir.parent

    resolved_path = str(Path(repo_path).resolve())
    verifier = get_patch_verifier()

    # Reconstruct Patch model from dictionary
    from app.patching.models import FilePatch, Patch, PatchStatus
    files_changed = [
        FilePatch(
            file_path=fp["file_path"],
            original_content=fp.get("original_content", ""),
            proposed_content=fp.get("proposed_content", ""),
            start_line=fp.get("start_line"),
            end_line=fp.get("end_line"),
            target_content=fp.get("target_content"),
            replacement=fp.get("replacement"),
        )
        for fp in patch_dict.get("files_changed", [])
    ]

    patch = Patch(
        patch_id=patch_dict.get("patch_id", "PATCH-UNKNOWN"),
        files_changed=files_changed,
        description=patch_dict.get("description", ""),
        reason=patch_dict.get("reason", ""),
        diff=patch_dict.get("diff", ""),
        confidence=patch_dict.get("confidence", 0.8),
        status=PatchStatus(patch_dict.get("status", "proposed")),
        iteration=patch_dict.get("iteration", 1),
    )

    verif_res = verifier.verify_patch(
        patch=patch,
        source_repo_path=resolved_path,
        targeted_test=targeted_test,
    )

    return {
        "success": verif_res.status.value in ("FIX_VERIFIED", "PRE_EXISTING_FAILURES"),
        "tool": "apply_and_verify_patch",
        "patch_id": verif_res.patch_id,
        "status": verif_res.status.value,
        "diff": verif_res.diff,
        "fixed_failures": verif_res.fixed_failures,
        "new_regressions": verif_res.new_regressions,
        "pre_existing_failures": verif_res.pre_existing_failures,
        "targeted_test_result": verif_res.targeted_test_result,
        "verification_result": verif_res.to_dict(),
    }
