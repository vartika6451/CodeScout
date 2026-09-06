import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path for direct execution or unittest runner
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.code_graph.analyzer import analyze_repository
from app.code_graph.models import Class, File, Function, ImportInfo, RepositoryAnalysis
from app.code_graph.parser import parse_python_file, parse_python_source


class TestCodeGraphParser(unittest.TestCase):
    """Unit tests for AST code parser covering all required scenarios."""

    def test_01_imports(self):
        """Test 1 — imports: import os, from database import connect, aliased imports."""
        code = """
import os
import numpy as np
from database import connect
from app.services.auth import AuthService
"""
        file_model = parse_python_source(code, "test_imports.py")

        self.assertEqual(len(file_model.imports), 4)

        # 1. import os
        imp_os = file_model.imports[0]
        self.assertEqual(imp_os.module, "os")
        self.assertEqual(imp_os.name, "os")
        self.assertIsNone(imp_os.alias)
        self.assertFalse(imp_os.is_from_import)
        self.assertEqual(imp_os.imported_as, "os")
        self.assertEqual(imp_os.line_number, 2)

        # 2. import numpy as np
        imp_np = file_model.imports[1]
        self.assertEqual(imp_np.module, "numpy")
        self.assertEqual(imp_np.name, "numpy")
        self.assertEqual(imp_np.alias, "np")
        self.assertFalse(imp_np.is_from_import)
        self.assertEqual(imp_np.imported_as, "np")

        # 3. from database import connect
        imp_db = file_model.imports[2]
        self.assertEqual(imp_db.module, "database")
        self.assertEqual(imp_db.name, "connect")
        self.assertIsNone(imp_db.alias)
        self.assertTrue(imp_db.is_from_import)
        self.assertEqual(imp_db.imported_as, "connect")

        # 4. from app.services.auth import AuthService
        imp_auth = file_model.imports[3]
        self.assertEqual(imp_auth.module, "app.services.auth")
        self.assertEqual(imp_auth.name, "AuthService")
        self.assertIsNone(imp_auth.alias)
        self.assertTrue(imp_auth.is_from_import)
        self.assertEqual(imp_auth.imported_as, "AuthService")

    def test_02_functions(self):
        """Test 2 — functions: def login(): pass."""
        code = """
def login():
    pass
"""
        file_model = parse_python_source(code, "test_funcs.py")

        self.assertEqual(len(file_model.functions), 1)
        fn = file_model.functions[0]
        self.assertEqual(fn.name, "login")
        self.assertEqual(fn.file_path, "test_funcs.py")
        self.assertEqual(fn.line_number, 2)
        self.assertFalse(fn.is_async)
        self.assertFalse(fn.is_method)
        self.assertEqual(fn.calls, [])

    def test_03_function_calls(self):
        """Test 3 — function calls: def login(): validate_user(); create_session()."""
        code = """
def login():
    validate_user()
    create_session()
"""
        file_model = parse_python_source(code, "test_calls.py")

        self.assertEqual(len(file_model.functions), 1)
        fn = file_model.functions[0]
        self.assertEqual(fn.name, "login")
        self.assertEqual(fn.calls, ["validate_user", "create_session"])

    def test_04_classes(self):
        """Test 4 — classes: class UserService: def login(self): pass."""
        code = """
class UserService:
    def login(self):
        pass
"""
        file_model = parse_python_source(code, "test_classes.py")

        # Top-level functions should be empty since login is a method
        self.assertEqual(len(file_model.functions), 0)
        self.assertEqual(len(file_model.classes), 1)

        cls = file_model.classes[0]
        self.assertEqual(cls.name, "UserService")
        self.assertEqual(cls.line_number, 2)
        self.assertEqual(cls.base_classes, [])
        self.assertEqual(len(cls.methods), 1)

        method = cls.methods[0]
        self.assertEqual(method.name, "login")
        self.assertTrue(method.is_method)
        self.assertEqual(method.class_name, "UserService")
        self.assertEqual(method.line_number, 3)

        # all_functions helper includes both top-level and methods
        self.assertEqual(len(file_model.all_functions), 1)
        self.assertEqual(file_model.all_functions[0].name, "login")

    def test_05_inheritance(self):
        """Test 5 — inheritance: class AdminService(UserService): pass."""
        code = """
class AdminService(UserService):
    pass
"""
        file_model = parse_python_source(code, "test_inheritance.py")

        self.assertEqual(len(file_model.classes), 1)
        cls = file_model.classes[0]
        self.assertEqual(cls.name, "AdminService")
        self.assertEqual(cls.base_classes, ["UserService"])

    def test_06_async_functions(self):
        """Test 6 — async functions: async def fetch_user(): ..."""
        code = """
async def fetch_user():
    pass
"""
        file_model = parse_python_source(code, "test_async.py")

        self.assertEqual(len(file_model.functions), 1)
        fn = file_model.functions[0]
        self.assertEqual(fn.name, "fetch_user")
        self.assertTrue(fn.is_async)

    def test_07_attribute_calls(self):
        """Test 7 — attribute calls: def login(): database.connect(); service.validate()."""
        code = """
def login():
    database.connect()
    service.validate()
"""
        file_model = parse_python_source(code, "test_attr_calls.py")

        self.assertEqual(len(file_model.functions), 1)
        fn = file_model.functions[0]
        self.assertEqual(fn.calls, ["database.connect", "service.validate"])

    def test_08_malformed_python(self):
        """Test 8 — malformed Python: unparseable file should not crash repository analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Valid file
            valid_file = temp_path / "valid.py"
            valid_file.write_text("def valid():\n    return True\n", encoding="utf-8")

            # Malformed file
            broken_file = temp_path / "broken.py"
            broken_file.write_text("def broken_syntax(:\n", encoding="utf-8")

            analysis = analyze_repository(temp_path)

            # Should analyze the valid file without raising an unhandled exception
            self.assertEqual(analysis.files_analyzed, 1)
            self.assertEqual(analysis.files[0].functions[0].name, "valid")

            # Malformed file must be recorded in parse_failures
            self.assertEqual(analysis.parse_failures_count, 1)
            self.assertIn(str(broken_file.resolve()), analysis.parse_failures)


class TestRepositoryAnalyzer(unittest.TestCase):
    """Tests for repository traversal and directory exclusions."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ignores_specified_directories(self):
        """Verify that excluded directories (.git, __pycache__, .venv, node_modules) are ignored."""
        # Create normal files
        (self.root / "app").mkdir()
        (self.root / "app" / "service.py").write_text(
            "import os\ndef run():\n    os.getcwd()\n",
            encoding="utf-8",
        )

        # Create ignored directories and files inside them
        ignored_dirs = [".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build"]
        for ign_dir in ignored_dirs:
            ign_path = self.root / ign_dir
            ign_path.mkdir()
            (ign_path / "ignored.py").write_text("def ignored_fn(): pass\n", encoding="utf-8")

        analysis = analyze_repository(self.root)

        self.assertEqual(analysis.files_analyzed, 1)
        self.assertEqual(analysis.functions_found, 1)
        self.assertEqual(analysis.files[0].functions[0].name, "run")
        self.assertEqual(analysis.parse_failures_count, 0)


if __name__ == "__main__":
    unittest.main()
