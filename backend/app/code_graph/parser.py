import ast
from pathlib import Path
from typing import List, Optional, Union

from app.code_graph.models import Class, File, Function, ImportInfo


def _extract_base_name(node: ast.AST) -> str:
    """Extracts a readable string representation of a base class expression."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        value_name = _extract_base_name(node.value)
        return f"{value_name}.{node.attr}" if value_name else node.attr
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _extract_call_name(func_node: ast.AST) -> Optional[str]:
    """Extracts a call identifier such as 'validate_user', 'db.connect', or 'user_service.login'."""
    if isinstance(func_node, ast.Name):
        return func_node.id
    elif isinstance(func_node, ast.Attribute):
        value_name = _extract_call_name(func_node.value)
        if value_name:
            return f"{value_name}.{func_node.attr}"
        return func_node.attr
    return None


class _CallVisitor(ast.NodeVisitor):
    """Visits nodes within a function body to extract call expressions in source order."""

    def __init__(self) -> None:
        self.calls: List[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _extract_call_name(node.func)
        if call_name:
            self.calls.append(call_name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Do not recurse into nested function bodies
        pass

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        # Do not recurse into nested async function bodies
        pass

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Do not recurse into nested class definitions
        pass


def _extract_calls(func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> List[str]:
    """Extracts calls made inside a function body."""
    visitor = _CallVisitor()
    for stmt in func_node.body:
        visitor.visit(stmt)
    return visitor.calls


class _CodeStructureVisitor(ast.NodeVisitor):
    """Traverses an AST tree to build structural models for File, Imports, Classes, and Functions."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.imports: List[ImportInfo] = []
        self.functions: List[Function] = []
        self.classes: List[Class] = []
        self._current_class: Optional[Class] = None
        self._inside_function: bool = False

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=alias.name,
                    name=alias.name,
                    alias=alias.asname,
                    is_from_import=False,
                    line_number=node.lineno,
                    end_line_number=getattr(node, "end_lineno", None),
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        level_prefix = "." * (node.level or 0)
        module_name = f"{level_prefix}{node.module or ''}"
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=module_name,
                    name=alias.name,
                    alias=alias.asname,
                    is_from_import=True,
                    line_number=node.lineno,
                    end_line_number=getattr(node, "end_lineno", None),
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        base_classes = [_extract_base_name(b) for b in node.bases]
        cls = Class(
            name=node.name,
            file_path=self.file_path,
            line_number=node.lineno,
            end_line_number=getattr(node, "end_lineno", None),
            base_classes=base_classes,
            methods=[],
        )

        is_top_level = self._current_class is None and not self._inside_function
        prev_class = self._current_class
        self._current_class = cls

        for item in node.body:
            self.visit(item)

        self._current_class = prev_class

        if is_top_level:
            self.classes.append(cls)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node, is_async=True)

    def _handle_function(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        is_async: bool,
    ) -> None:
        if self._inside_function:
            return

        calls = _extract_calls(node)
        func = Function(
            name=node.name,
            file_path=self.file_path,
            line_number=node.lineno,
            end_line_number=getattr(node, "end_lineno", None),
            calls=calls,
            is_async=is_async,
            is_method=self._current_class is not None,
            class_name=self._current_class.name if self._current_class else None,
        )

        if self._current_class is not None:
            self._current_class.methods.append(func)
        else:
            self.functions.append(func)

        prev_inside = self._inside_function
        self._inside_function = True

        # Scan function body for any localized import statements
        for stmt in node.body:
            for sub_node in ast.walk(stmt):
                if isinstance(sub_node, ast.Import):
                    self.visit_Import(sub_node)
                elif isinstance(sub_node, ast.ImportFrom):
                    self.visit_ImportFrom(sub_node)

        self._inside_function = prev_inside


def parse_python_source(source_code: str, file_path: str = "") -> File:
    """Parses a Python source code string into a structural File model using Python's ast module.

    Args:
        source_code: The Python code string to parse.
        file_path: The file path to associate with parsed elements.

    Returns:
        A File dataclass instance with imports, classes (and their methods), and functions.

    Raises:
        SyntaxError: If the source code contains invalid Python syntax.
    """
    tree = ast.parse(source_code, filename=file_path)
    visitor = _CodeStructureVisitor(file_path=file_path)
    visitor.visit(tree)

    return File(
        file_path=file_path,
        imports=visitor.imports,
        functions=visitor.functions,
        classes=visitor.classes,
    )


def parse_python_file(file_path: Union[str, Path]) -> File:
    """Reads and parses a Python file from disk into a structural File model.

    Args:
        file_path: Absolute or relative path to the Python file.

    Returns:
        A File dataclass instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        SyntaxError: If the file contains invalid Python syntax.
        UnicodeDecodeError: If the file cannot be decoded as UTF-8.
    """
    path_obj = Path(file_path)
    content = path_obj.read_text(encoding="utf-8")
    return parse_python_source(content, file_path=str(path_obj))
