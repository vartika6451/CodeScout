from pathlib import Path


ALLOWED_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".java",
    ".cpp",
    ".c",
    ".go",
    ".rs",
}


IGNORED_DIRECTORIES = {
    "node_modules",
    ".git",
    ".next",
    "dist",
    "build",
    "coverage",
    "venv",
    "__pycache__",
}


def should_analyze_file(path: str) -> bool:
    file_path = Path(path)

    if any(part in IGNORED_DIRECTORIES for part in file_path.parts):
        return False

    if file_path.name.endswith(".lock"):
        return False

    return file_path.suffix.lower() in ALLOWED_EXTENSIONS