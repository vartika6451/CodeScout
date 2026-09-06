import logging
from pathlib import Path
from typing import Optional, Tuple

from app.patching.diff import generate_unified_diff
from app.patching.models import FilePatch, Patch, PatchStatus
from app.patching.validator import PatchValidator

logger = logging.getLogger(__name__)


class PatchApplier:
    """
    Applies validated code patches strictly within an isolated workspace.
    Guarantees deterministic, localized file updates and accurate unified diff generation.
    """

    @classmethod
    def apply_patch(
        cls,
        patch: Patch,
        workspace_path: str,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Validates and applies a Patch to files inside the given workspace.

        Returns:
            Tuple of (success: bool, unified_diff: str, error_message: Optional[str])
        """
        # 1. Deterministic validation before modifying anything
        is_valid, err_msg = PatchValidator.validate_patch(patch, workspace_path)
        if not is_valid:
            logger.warning(f"Patch validation failed: {err_msg}")
            patch.status = PatchStatus.FAILED
            return False, "", err_msg

        ws_root = Path(workspace_path).resolve()
        applied_diffs = []

        try:
            for fp in patch.files_changed:
                target_file = ws_root / fp.file_path
                orig_text = target_file.read_text(encoding="utf-8", errors="replace")

                # Store snapshot of original content in FilePatch if not already set
                if not fp.original_content:
                    fp.original_content = orig_text

                # Compute new content
                new_text = cls._compute_new_content(fp, orig_text)
                fp.proposed_content = new_text

                # Generate individual unified diff
                diff = generate_unified_diff(orig_text, new_text, fp.file_path)
                applied_diffs.append(diff)

                # Write modified content to isolated workspace file
                target_file.write_text(new_text, encoding="utf-8")
                logger.info(f"Successfully applied patch to: {fp.file_path}")

            full_diff = "\n".join(d for d in applied_diffs if d.strip())
            patch.diff = full_diff
            patch.status = PatchStatus.APPLIED
            return True, full_diff, None

        except Exception as e:
            logger.error(f"Error applying patch to workspace: {e}", exc_info=True)
            patch.status = PatchStatus.FAILED
            return False, "", f"Failed to apply patch: {e}"

    @classmethod
    def revert_patch(
        cls,
        patch: Patch,
        workspace_path: str,
    ) -> bool:
        """
        Reverts the files changed by a patch back to their original content.
        """
        ws_root = Path(workspace_path).resolve()
        success = True

        for fp in patch.files_changed:
            target_file = ws_root / fp.file_path
            if target_file.is_file() and fp.original_content:
                try:
                    target_file.write_text(fp.original_content, encoding="utf-8")
                    logger.info(f"Reverted file to original content: {fp.file_path}")
                except Exception as e:
                    logger.error(f"Failed to revert {fp.file_path}: {e}")
                    success = False

        if success:
            patch.status = PatchStatus.REVERTED
        return success

    @classmethod
    def _compute_new_content(cls, file_patch: FilePatch, original_content: str) -> str:
        """
        Determines the new content by applying line range, target content replacement,
        or proposed content.
        """
        # Case 1: Line-based replacement (e.g. start_line=3, end_line=3)
        if (
            file_patch.start_line is not None
            and file_patch.end_line is not None
            and file_patch.replacement is not None
        ):
            lines = original_content.splitlines(keepends=True)
            start_idx = file_patch.start_line - 1
            end_idx = file_patch.end_line

            # Format replacement with newline if missing
            rep_text = file_patch.replacement
            if not rep_text.endswith("\n") and (end_idx < len(lines) or original_content.endswith("\n")):
                rep_text += "\n"

            new_lines = lines[:start_idx] + [rep_text] + lines[end_idx:]
            return "".join(new_lines)

        # Case 2: Substring target content replacement
        if file_patch.target_content and file_patch.replacement is not None:
            return original_content.replace(file_patch.target_content, file_patch.replacement, 1)

        # Case 3: Direct proposed content
        if file_patch.proposed_content:
            return file_patch.proposed_content

        return original_content
