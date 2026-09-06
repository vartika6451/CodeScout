import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple

from app.patching.models import FilePatch, Patch

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 1024 * 1024  # 1 MB
MAX_REPLACEMENT_SIZE = 100 * 1024  # 100 KB
FORBIDDEN_PATH_PATTERN = re.compile(r"[\;&\|`\$\>\<\\\x00]")


class PatchValidator:
    """
    Deterministic security and correctness validator for proposed code patches.
    Ensures patches are strictly confined within the isolated workspace and do not
    blindly overwrite unexpected file states.
    """

    @classmethod
    def validate_file_patch(
        cls,
        file_patch: FilePatch,
        workspace_path: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates an individual FilePatch against security and integrity rules.
        """
        rel_path = file_patch.file_path.strip()

        # 1. Reject forbidden characters & metacharacters in file path
        if FORBIDDEN_PATH_PATTERN.search(rel_path):
            return False, f"File path contains forbidden characters: {rel_path!r}"

        # 2. Reject path traversal
        if ".." in rel_path or rel_path.startswith("/") or rel_path.startswith("\\"):
            return False, f"Path traversal or absolute path rejected: {rel_path!r}"

        ws_root = Path(workspace_path).resolve()
        target_file = (ws_root / rel_path).resolve()

        # 3. Ensure target is strictly inside workspace root
        try:
            target_file.relative_to(ws_root)
        except ValueError:
            return False, f"Target file path escapes workspace root: {rel_path!r}"

        # 4. Reject symlinks to prevent symlink attacks
        if os.path.islink(target_file):
            return False, f"Target is a symlink, which is disallowed: {rel_path!r}"

        # 5. Check file existence
        if not target_file.is_file():
            return False, f"Target file does not exist in workspace: {rel_path!r}"

        # 6. Check file size
        file_size = target_file.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return False, f"Target file exceeds maximum allowed size ({file_size} > {MAX_FILE_SIZE} bytes)"

        # 7. Check replacement size
        if file_patch.replacement and len(file_patch.replacement.encode("utf-8")) > MAX_REPLACEMENT_SIZE:
            return False, f"Replacement exceeds maximum allowed size ({MAX_REPLACEMENT_SIZE} bytes)"

        # 8. Read current file content in workspace
        try:
            current_content = target_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return False, f"Failed to read target file: {e}"

        current_lines = current_content.splitlines()

        # 9. Line range validation if specified
        if file_patch.start_line is not None and file_patch.end_line is not None:
            if file_patch.start_line < 1:
                return False, f"start_line ({file_patch.start_line}) must be >= 1"
            if file_patch.end_line < file_patch.start_line:
                return False, f"end_line ({file_patch.end_line}) cannot be less than start_line ({file_patch.start_line})"
            if file_patch.start_line > len(current_lines) + 1:
                return False, f"start_line ({file_patch.start_line}) exceeds file line count ({len(current_lines)})"

        # 10. Verify target content if specified
        if file_patch.target_content:
            target_clean = file_patch.target_content.strip()
            if target_clean and target_clean not in current_content:
                return False, f"Expected target content was not found in {rel_path!r}"

        # 11. Verify expected original content if full content specified
        if file_patch.original_content and not file_patch.target_content and not file_patch.start_line:
            # Full file replacement: ensure current content matches expected original
            if current_content.strip() != file_patch.original_content.strip():
                return False, f"File {rel_path!r} content has changed since patch generation; blind overwrite rejected."

        return True, None

    @classmethod
    def validate_patch(
        cls,
        patch: Patch,
        workspace_path: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates all file modifications within a Patch.
        """
        if not patch.files_changed:
            return False, "Patch contains no file changes"

        for fp in patch.files_changed:
            is_valid, err = cls.validate_file_patch(fp, workspace_path)
            if not is_valid:
                return False, err

        return True, None
