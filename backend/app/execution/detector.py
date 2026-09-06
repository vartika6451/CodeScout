import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class FrameworkDetector:
    """Detects Python test frameworks and locates relevant test suites in a repository."""

    @staticmethod
    def detect_framework(repo_path: str, python_bin: Optional[str] = None) -> Tuple[str, bool]:
        """
        Inspects configuration files to detect the preferred test framework.
        Returns a tuple: (framework_name: "pytest" | "unittest", is_available: bool)
        """
        repo = Path(repo_path)
        is_pytest_configured = False

        # 1. Check pyproject.toml
        pyproject = repo / "pyproject.toml"
        if pyproject.is_file():
            try:
                content = pyproject.read_text(encoding="utf-8", errors="ignore")
                if "pytest" in content or "[tool.pytest" in content:
                    is_pytest_configured = True
            except Exception:
                pass

        # 2. Check pytest.ini / setup.cfg / tox.ini
        for cfg in ("pytest.ini", "setup.cfg", "tox.ini"):
            cfg_file = repo / cfg
            if cfg_file.is_file():
                try:
                    content = cfg_file.read_text(encoding="utf-8", errors="ignore")
                    if "pytest" in content:
                        is_pytest_configured = True
                        break
                except Exception:
                    pass

        # 3. Check requirements.txt
        req_file = repo / "requirements.txt"
        if req_file.is_file():
            try:
                content = req_file.read_text(encoding="utf-8", errors="ignore")
                if "pytest" in content:
                    is_pytest_configured = True
            except Exception:
                pass

        # 4. Check if pytest is available in the current Python environment
        py_executable = python_bin or sys.executable
        has_pytest_installed = False
        try:
            import importlib.util
            has_pytest_installed = importlib.util.find_spec("pytest") is not None
        except Exception:
            has_pytest_installed = False

        if is_pytest_configured and has_pytest_installed:
            return ("pytest", True)
        elif is_pytest_configured and not has_pytest_installed:
            # Configured but missing from environment
            return ("pytest", False)
        elif has_pytest_installed:
            # Not explicitly configured, but pytest is installed and can run python tests
            return ("pytest", True)

        # Standard library unittest is always available in Python
        return ("unittest", True)

    @staticmethod
    def build_test_command(
        framework: str,
        repo_path: str,
        target: Optional[str] = None,
        python_bin: Optional[str] = None,
    ) -> List[str]:
        """
        Constructs a safe argument vector for invoking the test runner.
        Never executes via shell.
        """
        py_bin = python_bin or sys.executable

        if framework == "pytest":
            cmd = [py_bin, "-m", "pytest", "-v"]
            if target:
                cmd.append(target)
            return cmd

        # Unittest
        if target:
            # Target can be a path like tests/test_login.py or dot-separated tests.test_login
            clean_target = target.replace("/", ".").replace("\\", ".")
            if clean_target.endswith(".py"):
                clean_target = clean_target[:-3]
            return [py_bin, "-m", "unittest", clean_target]

        # Discover test directory
        repo = Path(repo_path)
        test_dir = "tests" if (repo / "tests").is_dir() else ("test" if (repo / "test").is_dir() else ".")
        return [py_bin, "-m", "unittest", "discover", "-s", test_dir]

    @staticmethod
    def find_candidate_tests(
        repo_path: str,
        symbols: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Finds existing test files in the repository, prioritized by relevance to suspect symbols/files.
        """
        repo = Path(repo_path)
        if not repo.is_dir():
            return []

        # Find all test files
        test_files: List[str] = []
        for root, _, filenames in os.walk(repo_path):
            # Skip hidden, virtualenvs, cache, etc.
            rel_root = os.path.relpath(root, repo_path)
            parts = Path(rel_root).parts
            if any(p.startswith(".") or p in ("venv", "node_modules", "__pycache__") for p in parts):
                continue

            for fname in filenames:
                if (fname.startswith("test_") or fname.endswith("_test.py")) and fname.endswith(".py"):
                    full_rel = os.path.join(rel_root, fname) if rel_root != "." else fname
                    test_files.append(full_rel)

        if not test_files:
            return []

        # Score test files based on relevance
        ranked: List[Tuple[int, str]] = []
        file_basenames = [Path(f).stem.lower().replace("test_", "").replace("_test", "") for f in (files or [])]
        symbol_names = [s.lower() for s in (symbols or [])]

        for tf in test_files:
            score = 0
            tf_lower = tf.lower()
            tf_stem = Path(tf).stem.lower().replace("test_", "").replace("_test", "")

            # Match against suspect file stems
            for fb in file_basenames:
                if fb and (fb in tf_stem or tf_stem in fb):
                    score += 10

            # Match against suspect symbols
            for sym in symbol_names:
                if sym and sym in tf_lower:
                    score += 5

            ranked.append((score, tf))

        ranked.sort(key=lambda x: x[0], reverse=True)
        return [tf for _, tf in ranked]
