import difflib
from typing import Optional

from app.patching.models import FilePatch, Patch


def generate_unified_diff(
    original_content: str,
    proposed_content: str,
    file_path: str,
) -> str:
    """
    Generates a standard, human-readable Unified Diff comparing original and proposed code.

    Format matches Git unified diff standards:
    --- a/path/to/file.py
    +++ b/path/to/file.py
    @@ -1,5 +1,5 @@
    """
    clean_path = file_path.replace("\\", "/").lstrip("/")
    orig_lines = original_content.splitlines(keepends=True)
    prop_lines = proposed_content.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            orig_lines,
            prop_lines,
            fromfile=f"a/{clean_path}",
            tofile=f"b/{clean_path}",
        )
    )

    return "".join(diff_lines)


def generate_patch_diff(patch: Patch) -> str:
    """
    Aggregates unified diffs across all changed files in a patch.
    """
    all_diffs = []
    for fp in patch.files_changed:
        d = generate_unified_diff(
            original_content=fp.original_content,
            proposed_content=fp.proposed_content,
            file_path=fp.file_path,
        )
        if d.strip():
            all_diffs.append(d)

    return "\n".join(all_diffs)
