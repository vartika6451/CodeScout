import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.agents.tools import (
    find_callees,
    find_callers,
    find_definition,
    find_references,
    get_class_info,
    get_dependencies,
    get_dependents,
    get_file_structure,
    search_code,
    trace_function,
)
from app.code_graph import build_code_graph


class TestAgentTools(unittest.TestCase):
    """Unit tests for the 10 CodeScout codebase investigation tools."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)

        # Build a fixture codebase for testing all tool permutations
        (self.root / "auth.py").write_text(
            """
class AuthService:
    def validate_token(self, token: str):
        return True

    def login(self, username: str):
        self.validate_token(username)
        return "session_token"

def create_session():
    return "session"
""",
            encoding="utf-8",
        )

        (self.root / "app.py").write_text(
            """
from auth import AuthService, create_session

class AppController:
    def __init__(self):
        self.auth = AuthService()

    def handle_login(self, username: str):
        self.auth.login(username)
        create_session()
""",
            encoding="utf-8",
        )

        (self.root / "cycle.py").write_text(
            """
def func_a():
    func_b()

def func_b():
    func_c()

def func_c():
    func_a()
""",
            encoding="utf-8",
        )

        self.graph = build_code_graph(self.root)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_search_code_standardized_shape(self):
        """Test 1 — search_code: returns predictable standardized format."""
        res = search_code("test query", repository="mock/repo")
        self.assertIn("success", res)
        self.assertIn("tool", res)
        self.assertEqual(res["tool"], "search_code")
        self.assertIn("results", res)
        self.assertIsInstance(res["results"], list)

    def test_02_find_definition_valid_and_missing(self):
        """Test 2 — find_definition: valid symbol returns location; missing symbol returns error."""
        # Valid function/method
        res = find_definition("AuthService.login", graph=self.graph)
        self.assertTrue(res["success"])
        self.assertEqual(res["definition"]["name"], "login")
        self.assertEqual(res["definition"]["type"], "METHOD")
        self.assertEqual(res["definition"]["file_path"], "auth.py")

        # Missing symbol
        res_missing = find_definition("NonExistentSymbol", graph=self.graph)
        self.assertFalse(res_missing["success"])
        self.assertIn("not found", res_missing["error"])

    def test_03_find_callees(self):
        """Test 3 — find_callees: discovers called methods/functions."""
        res = find_callees("AuthService.login", graph=self.graph)
        self.assertTrue(res["success"])
        callee_names = [c["name"] for c in res["callees"]]
        self.assertIn("validate_token", callee_names)

        # Missing symbol
        res_missing = find_callees("DoesNotExist", graph=self.graph)
        self.assertFalse(res_missing["success"])

    def test_04_find_callers(self):
        """Test 4 — find_callers: discovers calling functions."""
        res = find_callers("create_session", graph=self.graph)
        self.assertTrue(res["success"])
        caller_names = [c["name"] for c in res["callers"]]
        self.assertIn("handle_login", caller_names)

        # Missing symbol
        res_missing = find_callers("DoesNotExist", graph=self.graph)
        self.assertFalse(res_missing["success"])

    def test_05_find_references(self):
        """Test 5 — find_references: distinguishes definition from call sites and import sites."""
        res = find_references("create_session", graph=self.graph)
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["definition"])
        self.assertEqual(res["definition"]["file_path"], "auth.py")
        self.assertTrue(res["total_references"] > 0)

        # Call site in app.py
        call_files = [c["file_path"] for c in res["references"]["call_sites"]]
        self.assertIn("app.py", call_files)

    def test_06_get_file_structure(self):
        """Test 6 — get_file_structure: lists classes, methods, functions, and imports."""
        res = get_file_structure("auth.py", graph=self.graph)
        self.assertTrue(res["success"])
        cls_names = [c["name"] for c in res["classes"]]
        fn_names = [f["name"] for f in res["functions"]]
        self.assertIn("AuthService", cls_names)
        self.assertIn("create_session", fn_names)

        # Missing file
        res_missing = get_file_structure("non_existent_file.py", graph=self.graph)
        self.assertFalse(res_missing["success"])
        self.assertIn("not found", res_missing["error"])

    def test_07_get_class_info(self):
        """Test 7 — get_class_info: inspects class methods, base classes, subclasses."""
        res = get_class_info("AuthService", graph=self.graph)
        self.assertTrue(res["success"])
        method_names = [m["name"] for m in res["methods"]]
        self.assertIn("login", method_names)
        self.assertIn("validate_token", method_names)

        # Missing class
        res_missing = get_class_info("UnknownClass", graph=self.graph)
        self.assertFalse(res_missing["success"])

    def test_08_trace_function_depth_and_cycle_protection(self):
        """Test 8 — trace_function: builds call tree, respects depth, and handles cycles."""
        # Cycle testing: func_a -> func_b -> func_c -> func_a
        res = trace_function("func_a", depth=4, graph=self.graph)
        self.assertTrue(res["success"])
        tree = res["tree"]
        self.assertEqual(tree["name"], "func_a")
        self.assertEqual(len(tree["calls"]), 1)
        b_node = tree["calls"][0]
        self.assertEqual(b_node["name"], "func_b")
        c_node = b_node["calls"][0]
        self.assertEqual(c_node["name"], "func_c")

        # Third hop should detect the cycle and terminate safely
        cycle_node = c_node["calls"][0]
        self.assertTrue(cycle_node.get("is_cycle"))
        self.assertEqual(cycle_node["calls"], [])

    def test_09_get_dependencies(self):
        """Test 9 — get_dependencies: reveals imports and called external symbols."""
        res = get_dependencies("app.py", graph=self.graph)
        self.assertTrue(res["success"])
        self.assertIn("auth.py", res["imported_files"])

    def test_10_get_dependents(self):
        """Test 10 — get_dependents: reveals incoming imports and external callers."""
        res = get_dependents("auth.py", graph=self.graph)
        self.assertTrue(res["success"])
        self.assertIn("app.py", res["dependent_files"])


if __name__ == "__main__":
    unittest.main()
