import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger(__name__)

# Directory names and file patterns excluded when copying into isolated workspaces
EXCLUDE_DIRS: Set[str] = {
    ".git",
    "venv",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
    ".gemini",
}


class IsolatedWorkspace:
    """
    Manages an isolated working copy of a repository in a secure temporary directory.
    Guarantees that the original source repository is NEVER modified during automated
    patch generation, application, and test verification.
    """

    def __init__(
        self,
        source_repo_path: str,
        preserve_on_exit: bool = False,
    ):
        self.source_repo_path = str(Path(source_repo_path).resolve())
        self.preserve_on_exit = preserve_on_exit
        self.workspace_path: Optional[str] = None
        self._is_active = False

    def setup(self) -> str:
        """
        Creates an isolated temporary directory and populates it with a clean snapshot
        of the source repository.
        """
        if self._is_active and self.workspace_path and Path(self.workspace_path).is_dir():
            return self.workspace_path

        temp_dir = tempfile.mkdtemp(prefix="codescout_ws_")
        self.workspace_path = temp_dir
        self._copy_repository_files(self.source_repo_path, temp_dir)
        self._is_active = True
        logger.info(f"Isolated workspace created at: {temp_dir}")
        return temp_dir

    def reset(self) -> None:
        """
        Discards any modifications in the workspace and restores it to a pristine state
        matching the original source repository.
        """
        if not self.workspace_path or not Path(self.workspace_path).is_dir():
            self.setup()
            return

        # Clear existing workspace contents
        for item in os.listdir(self.workspace_path):
            item_path = os.path.join(self.workspace_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
            else:
                try:
                    os.remove(item_path)
                except OSError:
                    pass

        # Re-populate from original source repository
        self._copy_repository_files(self.source_repo_path, self.workspace_path)
        logger.info(f"Workspace at {self.workspace_path} reset to clean baseline.")

    def cleanup(self) -> None:
        """Destroys the temporary workspace directory."""
        if self.workspace_path and Path(self.workspace_path).is_dir():
            if not self.preserve_on_exit:
                shutil.rmtree(self.workspace_path, ignore_errors=True)
                logger.info(f"Cleaned up workspace at: {self.workspace_path}")
            else:
                logger.info(f"Preserving workspace at: {self.workspace_path} for user review.")
            self._is_active = False
            self.workspace_path = None

    def _copy_repository_files(self, src: str, dst: str) -> None:
        """Recursively copies repository files while safely ignoring caches and virtualenvs."""
        src_path = Path(src)
        dst_path = Path(dst)

        for root, dirs, files in os.walk(src):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]

            rel_dir = os.path.relpath(root, src)
            target_dir = dst_path if rel_dir == "." else dst_path / rel_dir
            target_dir.mkdir(parents=True, exist_ok=True)

            for file in files:
                if file.startswith(".") and file not in (".env.example", ".gitignore"):
                    continue
                if file.endswith((".pyc", ".pyo")):
                    continue

                src_file = Path(root) / file
                dst_file = target_dir / file
                try:
                    shutil.copy2(src_file, dst_file)
                except Exception as e:
                    logger.debug(f"Failed to copy file {src_file}: {e}")

    def __enter__(self) -> str:
        return self.setup()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
