import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.code_graph import (
    CodeGraph,
    EdgeType,
    Node,
    NodeType,
    build_code_graph,
)


class TestSymbolResolution(unittest.TestCase):
    """Unit tests for Phase 1 — Part 2: Code Graph & Symbol Resolution."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_same_file_call(self):
        """Test 1 — Same-file call: def a(): pass; def b(): a() -> b CALLS a."""
        src = """
def a():
    pass

def b():
    a()
"""
        (self.root / "module_a.py").write_text(src, encoding="utf-8")
        graph = build_code_graph(self.root)

        callees_of_b = graph.get_callees("b")
        self.assertEqual(len(callees_of_b), 1)
        self.assertEqual(callees_of_b[0].name, "a")

        callers_of_a = graph.get_callers("a")
        self.assertEqual(len(callers_of_a), 1)
        self.assertEqual(callers_of_a[0].name, "b")

    def test_02_imported_function(self):
        """Test 2 — Imported function: from auth import validate; def login(): validate()."""
        auth_src = """
def validate():
    pass
"""
        app_src = """
from auth import validate

def login():
    validate()
"""
        (self.root / "auth.py").write_text(auth_src, encoding="utf-8")
        (self.root / "app.py").write_text(app_src, encoding="utf-8")

        graph = build_code_graph(self.root)

        callees_of_login = graph.get_callees("login")
        self.assertEqual(len(callees_of_login), 1)
        self.assertEqual(callees_of_login[0].name, "validate")
        self.assertEqual(callees_of_login[0].file_path, "auth.py")

        callers_of_validate = graph.get_callers("validate")
        self.assertEqual(len(callers_of_validate), 1)
        self.assertEqual(callers_of_validate[0].name, "login")

    def test_03_method_call(self):
        """Test 3 — Method call: class Service: def validate(self): pass; def login(self): self.validate()."""
        src = """
class Service:
    def validate(self):
        pass

    def login(self):
        self.validate()
"""
        (self.root / "service.py").write_text(src, encoding="utf-8")
        graph = build_code_graph(self.root)

        login_node = graph.get_definition("Service.login")
        self.assertIsNotNone(login_node)

        callees = graph.get_callees("Service.login")
        self.assertEqual(len(callees), 1)
        self.assertEqual(callees[0].name, "validate")
        self.assertEqual(callees[0].type, NodeType.METHOD)

    def test_04_inheritance(self):
        """Test 4 — Inheritance: class Base: pass; class Child(Base): pass -> Child INHERITS Base."""
        src = """
class Base:
    pass

class Child(Base):
    pass
"""
        (self.root / "models.py").write_text(src, encoding="utf-8")
        graph = build_code_graph(self.root)

        base_classes = graph.get_base_classes("Child")
        self.assertEqual(len(base_classes), 1)
        self.assertEqual(base_classes[0].name, "Base")

        subclasses = graph.get_subclasses("Base")
        self.assertEqual(len(subclasses), 1)
        self.assertEqual(subclasses[0].name, "Child")

    def test_05_multiple_callers(self):
        """Test 5 — Multiple callers: validate called by login and register."""
        src = """
def validate():
    pass

def login():
    validate()

def register():
    validate()
"""
        (self.root / "auth.py").write_text(src, encoding="utf-8")
        graph = build_code_graph(self.root)

        callers = graph.get_callers("validate")
        caller_names = {c.name for c in callers}
        self.assertEqual(caller_names, {"login", "register"})

    def test_06_ambiguous_symbol(self):
        """Test 6 — Ambiguous symbol: multiple definitions across modules with no import; do NOT invent edge."""
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "auth.py").write_text(
            "def validate_user(): pass\n",
            encoding="utf-8",
        )
        (self.root / "pkg" / "admin.py").write_text(
            "def validate_user(): pass\n",
            encoding="utf-8",
        )
        (self.root / "pkg" / "caller.py").write_text(
            "def check():\n    validate_user()\n",
            encoding="utf-8",
        )

        graph = build_code_graph(self.root)

        # check() should have 0 callees because validate_user is ambiguous and was never imported
        callees = graph.get_callees("check")
        self.assertEqual(len(callees), 0)

        # Must record ambiguous call in unresolved_calls telemetry
        ambiguous = [c for c in graph.unresolved_calls if c.reason == "ambiguous"]
        self.assertEqual(len(ambiguous), 1)
        self.assertEqual(ambiguous[0].call_name, "validate_user")
        self.assertEqual(len(ambiguous[0].candidates), 2)

    def test_07_missing_or_external_symbol(self):
        """Test 7 — Missing/external symbol: calling an unresolvable function does not crash."""
        src = """
def login():
    external_function()
    print("logged in")
"""
        (self.root / "app.py").write_text(src, encoding="utf-8")
        graph = build_code_graph(self.root)

        callees = graph.get_callees("login")
        self.assertEqual(len(callees), 0)

        external_calls = [c for c in graph.unresolved_calls if c.reason == "external_or_missing"]
        call_names = {c.call_name for c in external_calls}
        self.assertIn("external_function", call_names)
        self.assertIn("print", call_names)

    def test_08_reverse_lookup_and_file_symbols(self):
        """Test 8 — Reverse lookup APIs: get_definition, get_class_methods, get_file_symbols."""
        src = """
class UserService:
    def login(self):
        pass

    def logout(self):
        pass

def helper():
    pass
"""
        (self.root / "users.py").write_text(src, encoding="utf-8")
        graph = build_code_graph(self.root)

        # get_definition
        svc_node = graph.get_definition("UserService")
        self.assertIsNotNone(svc_node)
        self.assertEqual(svc_node.type, NodeType.CLASS)

        # get_class_methods
        methods = graph.get_class_methods("UserService")
        method_names = {m.name for m in methods}
        self.assertEqual(method_names, {"login", "logout"})

        # get_file_symbols
        symbols = graph.get_file_symbols("users.py")
        sym_names = {s.name for s in symbols}
        self.assertEqual(sym_names, {"UserService", "login", "logout", "helper"})


if __name__ == "__main__":
    unittest.main()
