import logging
import os
from pathlib import Path
from typing import Optional, Set, Union

from app.code_graph.models import RepositoryAnalysis
from app.code_graph.parser import parse_python_file

logger = logging.getLogger(__name__)

DEFAULT_IGNORED_DIRECTORIES: Set[str] = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vscode",
    "eggs",
    ".eggs",
}


def analyze_repository(
    repo_path: Union[str, Path],
    ignored_directories: Optional[Set[str]] = None,
) -> RepositoryAnalysis:
    """Recursively analyzes all Python files in a repository and extracts structural models.

    Args:
        repo_path: Path to the directory or repository to analyze.
        ignored_directories: Set of directory names to skip during recursion. Defaults to
            DEFAULT_IGNORED_DIRECTORIES (.git, __pycache__, .venv, venv, node_modules, etc.).

    Returns:
        A RepositoryAnalysis object containing parsed File models and any parse failures.

    Raises:
        FileNotFoundError: If repo_path does not exist.
    """
    path_obj = Path(repo_path).resolve()

    if not path_obj.exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

    ignored_dirs = (
        ignored_directories
        if ignored_directories is not None
        else DEFAULT_IGNORED_DIRECTORIES
    )

    analysis = RepositoryAnalysis(repo_path=str(path_obj))

    # Single-file support
    if path_obj.is_file():
        if path_obj.suffix.lower() == ".py":
            try:
                parsed_file = parse_python_file(path_obj)
                analysis.files.append(parsed_file)
            except Exception as exc:
                logger.warning("Failed to parse %s: %s", path_obj, exc)
                analysis.parse_failures[str(path_obj)] = str(exc)
        return analysis

    for root, dirs, filenames in os.walk(path_obj):
        # Prune ignored directories in-place to prevent traversing into them
        dirs[:] = sorted([d for d in dirs if d not in ignored_dirs])

        for filename in sorted(filenames):
            if filename.endswith(".py"):
                file_path = Path(root) / filename
                try:
                    parsed_file = parse_python_file(file_path)
                    analysis.files.append(parsed_file)
                except Exception as exc:
                    logger.warning("Failed to parse %s: %s", file_path, exc)
                    analysis.parse_failures[str(file_path)] = str(exc)

    return analysis
