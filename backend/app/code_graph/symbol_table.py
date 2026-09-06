from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.code_graph.models import Class, File, Function, ImportInfo, Node, NodeType


def normalize_file_path(file_path: str, repo_path: str) -> str:
    """Normalizes a file path to be relative to the repository root where possible."""
    try:
        resolved_file = Path(file_path).resolve()
        resolved_repo = Path(repo_path).resolve()
        return str(resolved_file.relative_to(resolved_repo))
    except (ValueError, Exception):
        return Path(file_path).name


def get_module_name(relative_file_path: str) -> str:
    """Computes the Python module dot-path for a relative file path."""
    p = Path(relative_file_path)
    parts = list(p.parts)
    if not parts:
        return ""

    # Strip .py extension from the last part
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]

    # If __init__, the module name is the package directory
    if parts[-1] == "__init__":
        parts.pop()

    return ".".join(parts)


def resolve_relative_module(import_module: str, current_module: str) -> str:
    """Resolves relative import paths (e.g., .models, ..services) against current module."""
    if not import_module.startswith("."):
        return import_module

    dot_count = 0
    while dot_count < len(import_module) and import_module[dot_count] == ".":
        dot_count += 1

    remainder = import_module[dot_count:]
    module_parts = current_module.split(".") if current_module else []
    pkg_parts = module_parts[:-1] if module_parts else []

    steps_up = dot_count - 1
    if steps_up > 0:
        pkg_parts = pkg_parts[:-steps_up] if steps_up <= len(pkg_parts) else []

    if remainder:
        pkg_parts.append(remainder)

    return ".".join(pkg_parts)


class SymbolTable:
    """Maintains symbol indexes across the repository for deterministic resolution."""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path

        # Primary indexes
        self.nodes_by_id: Dict[str, Node] = {}
        self.fully_qualified: Dict[str, Node] = {}
        self.simple_names: Dict[str, List[Node]] = {}
        self.file_symbols: Dict[str, List[Node]] = {}
        self.file_nodes: Dict[str, Node] = {}
        self.file_imports: Dict[str, List[ImportInfo]] = {}
        self.classes_by_name: Dict[str, List[Node]] = {}
        self.module_to_file: Dict[str, str] = {}

    def register_file(self, file_model: File) -> Node:
        """Registers a File and creates its FILE node."""
        rel_path = normalize_file_path(file_model.file_path, self.repo_path)
        module_name = get_module_name(rel_path)

        file_node_id = f"file::{rel_path}"
        file_node = Node(
            id=file_node_id,
            name=rel_path,
            type=NodeType.FILE,
            file_path=rel_path,
            line_number=1,
            properties={"module_name": module_name, "raw_path": file_model.file_path},
        )

        self.nodes_by_id[file_node.id] = file_node
        self.file_nodes[rel_path] = file_node
        self.file_imports[rel_path] = file_model.imports
        if module_name:
            self.module_to_file[module_name] = rel_path
            # Also register intermediate package prefixes
            parts = module_name.split(".")
            for i in range(1, len(parts)):
                sub_mod = ".".join(parts[i:])
                if sub_mod not in self.module_to_file:
                    self.module_to_file[sub_mod] = rel_path

        return file_node

    def register_class(self, cls_model: Class, file_node: Node) -> Node:
        """Registers a Class and creates its CLASS node."""
        rel_path = file_node.file_path
        module_name = file_node.properties.get("module_name", "")
        class_node_id = (
            f"python::{module_name}::{cls_model.name}"
            if module_name
            else f"python::{rel_path}::{cls_model.name}"
        )

        class_node = Node(
            id=class_node_id,
            name=cls_model.name,
            type=NodeType.CLASS,
            file_path=rel_path,
            line_number=cls_model.line_number,
            end_line_number=cls_model.end_line_number,
            parent_id=file_node.id,
            properties={
                "base_classes": cls_model.base_classes,
                "module_name": module_name,
            },
        )

        self._index_symbol(class_node, module_name)
        self.classes_by_name.setdefault(cls_model.name, []).append(class_node)
        return class_node

    def register_function(
        self,
        fn_model: Function,
        file_node: Node,
        class_node: Optional[Node] = None,
    ) -> Node:
        """Registers a Function or Method and creates its corresponding Node."""
        rel_path = file_node.file_path
        module_name = file_node.properties.get("module_name", "")

        if fn_model.is_method and class_node is not None:
            node_id = f"{class_node.id}.{fn_model.name}"
            node_type = NodeType.METHOD
            parent_id = class_node.id
        else:
            node_id = (
                f"python::{module_name}::{fn_model.name}"
                if module_name
                else f"python::{rel_path}::{fn_model.name}"
            )
            node_type = NodeType.FUNCTION
            parent_id = file_node.id

        fn_node = Node(
            id=node_id,
            name=fn_model.name,
            type=node_type,
            file_path=rel_path,
            line_number=fn_model.line_number,
            end_line_number=fn_model.end_line_number,
            parent_id=parent_id,
            properties={
                "is_async": fn_model.is_async,
                "calls": fn_model.calls,
                "class_name": class_node.name if class_node else None,
                "module_name": module_name,
            },
        )

        self._index_symbol(fn_node, module_name, class_node.name if class_node else None)
        return fn_node

    def _index_symbol(
        self,
        node: Node,
        module_name: str,
        class_name: Optional[str] = None,
    ) -> None:
        """Helper to index a symbol across ID, qualified names, and simple name tables."""
        self.nodes_by_id[node.id] = node

        # Index by simple name
        self.simple_names.setdefault(node.name, []).append(node)

        # Index by file symbols
        self.file_symbols.setdefault(node.file_path, []).append(node)

        # Index by fully qualified dot-paths
        if class_name:
            qual_name = f"{class_name}.{node.name}"
            self.fully_qualified[qual_name] = node
            if module_name:
                self.fully_qualified[f"{module_name}.{qual_name}"] = node
                # Also index sub-module paths
                parts = module_name.split(".")
                for i in range(1, len(parts)):
                    self.fully_qualified[f"{'.'.join(parts[i:])}.{qual_name}"] = node
        else:
            self.fully_qualified[node.name] = node
            if module_name:
                self.fully_qualified[f"{module_name}.{node.name}"] = node
                parts = module_name.split(".")
                for i in range(1, len(parts)):
                    self.fully_qualified[f"{'.'.join(parts[i:])}.{node.name}"] = node

    def resolve_call(
        self,
        caller_node: Node,
        call_name: str,
    ) -> Tuple[Optional[Node], str, List[str]]:
        """Resolves a function/method call to a target Node.

        Returns:
            (target_node, status, candidates)
            status can be: 'resolved', 'ambiguous', or 'unresolved'
        """
        file_path = caller_node.file_path
        current_module = caller_node.properties.get("module_name", "")

        # -------------------------------------------------------------
        # 1. Method call on self.<method>() or cls.<method>()
        # -------------------------------------------------------------
        if call_name.startswith("self.") or call_name.startswith("cls."):
            method_name = call_name.split(".", 1)[1]
            if caller_node.parent_id and caller_node.type == NodeType.METHOD:
                class_node = self.nodes_by_id.get(caller_node.parent_id)
                if class_node:
                    # Look for method in current class
                    for sym in self.file_symbols.get(file_path, []):
                        if (
                            sym.type == NodeType.METHOD
                            and sym.parent_id == class_node.id
                            and sym.name == method_name
                        ):
                            return sym, "resolved", []

                    # Look for method in base classes
                    for base_name in class_node.properties.get("base_classes", []):
                        base_classes = self.classes_by_name.get(base_name, [])
                        for base_cls in base_classes:
                            for sym in self.nodes_by_id.values():
                                if (
                                    sym.type == NodeType.METHOD
                                    and sym.parent_id == base_cls.id
                                    and sym.name == method_name
                                ):
                                    return sym, "resolved", []

            return None, "unresolved", []

        # -------------------------------------------------------------
        # 2. Local definition in the same file
        # -------------------------------------------------------------
        if "." not in call_name:
            for sym in self.file_symbols.get(file_path, []):
                if sym.type in (NodeType.FUNCTION, NodeType.CLASS) and sym.name == call_name:
                    return sym, "resolved", []

        # -------------------------------------------------------------
        # 3. Explicit imported symbols in the same file
        # -------------------------------------------------------------
        imports = self.file_imports.get(file_path, [])
        for imp in imports:
            # Case 3a: from x import y (or from x import y as z)
            if imp.imported_as == call_name:
                mod = resolve_relative_module(imp.module or "", current_module)
                target_qual = f"{mod}.{imp.name}" if mod else imp.name

                # Look up target_qual in fully_qualified
                target = self._find_in_fully_qualified(target_qual, imp.name)
                if target:
                    return target, "resolved", []
                return None, "unresolved", []

            # Case 3b: import x / import x as y; call is y.func()
            if "." in call_name:
                prefix, suffix = call_name.split(".", 1)
                if imp.imported_as == prefix:
                    mod = resolve_relative_module(imp.module or imp.name, current_module)
                    target_qual = f"{mod}.{suffix}"
                    target = self._find_in_fully_qualified(target_qual, suffix)
                    if target:
                        return target, "resolved", []
                    return None, "unresolved", []

        # -------------------------------------------------------------
        # 4. Attribute call on a class defined in the same file
        #    e.g. MyClass.some_method()
        # -------------------------------------------------------------
        if "." in call_name:
            prefix, suffix = call_name.split(".", 1)
            for sym in self.file_symbols.get(file_path, []):
                if sym.type == NodeType.CLASS and sym.name == prefix:
                    for method in self.nodes_by_id.values():
                        if (
                            method.type == NodeType.METHOD
                            and method.parent_id == sym.id
                            and method.name == suffix
                        ):
                            return method, "resolved", []

        # -------------------------------------------------------------
        # 5. Direct match in fully qualified table
        # -------------------------------------------------------------
        if "." in call_name:
            target = self._find_in_fully_qualified(call_name, call_name.split(".")[-1])
            if target:
                return target, "resolved", []

        # -------------------------------------------------------------
        # 6. Global Simple-Name Disambiguation Safety
        # -------------------------------------------------------------
        candidates = self.simple_names.get(call_name, [])
        if len(candidates) > 1:
            # Ambiguous! Do NOT create a false edge.
            return None, "ambiguous", [c.id for c in candidates]

        return None, "unresolved", []

    def _find_in_fully_qualified(self, qual_name: str, simple_name: str) -> Optional[Node]:
        """Searches fully_qualified index by exact name and common module suffix variants."""
        if qual_name in self.fully_qualified:
            return self.fully_qualified[qual_name]

        for key, node in self.fully_qualified.items():
            if key.endswith(qual_name) and node.name == simple_name:
                return node

        return None

    def resolve_inheritance(self, class_node: Node, base_name: str) -> Optional[Node]:
        """Resolves a base class name to a target CLASS Node."""
        file_path = class_node.file_path
        current_module = class_node.properties.get("module_name", "")

        # 1. Base class defined in same file
        for sym in self.file_symbols.get(file_path, []):
            if sym.type == NodeType.CLASS and sym.name == base_name:
                return sym

        # 2. Base class explicitly imported
        for imp in self.file_imports.get(file_path, []):
            if imp.imported_as == base_name:
                mod = resolve_relative_module(imp.module or "", current_module)
                qual = f"{mod}.{imp.name}" if mod else imp.name
                target = self._find_in_fully_qualified(qual, imp.name)
                if target and target.type == NodeType.CLASS:
                    return target

        # 3. Unique match by class name
        candidates = self.classes_by_name.get(base_name, [])
        if len(candidates) == 1:
            return candidates[0]

        return None
