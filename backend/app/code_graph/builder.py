from pathlib import Path
from typing import Optional, Set, Union

from app.code_graph.analyzer import analyze_repository
from app.code_graph.graph import CodeGraph
from app.code_graph.models import EdgeType, Node, NodeType, UnresolvedCall
from app.code_graph.symbol_table import (
    SymbolTable,
    normalize_file_path,
    resolve_relative_module,
)


class GraphBuilder:
    """Orchestrates building a CodeGraph from repository source code analysis."""

    def __init__(
        self,
        repo_path: Union[str, Path],
        ignored_directories: Optional[Set[str]] = None,
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.ignored_directories = ignored_directories
        self.symbol_table = SymbolTable(repo_path=str(self.repo_path))
        self.graph = CodeGraph()

    def build(self) -> CodeGraph:
        """Executes full extraction, registration, and relationship resolution pipeline."""
        # Step 1: Run Part 1 AST analysis
        analysis = analyze_repository(
            self.repo_path,
            ignored_directories=self.ignored_directories,
        )

        # Step 2: Register structural entities & definition edges
        for file_model in analysis.files:
            file_node = self.symbol_table.register_file(file_model)
            self.graph.add_node(file_node)

            # Register classes and their methods
            for cls_model in file_model.classes:
                class_node = self.symbol_table.register_class(cls_model, file_node)
                self.graph.add_node(class_node)
                self.graph.add_edge(file_node.id, class_node.id, EdgeType.DEFINES)

                for method_model in cls_model.methods:
                    method_node = self.symbol_table.register_function(
                        method_model,
                        file_node,
                        class_node=class_node,
                    )
                    self.graph.add_node(method_node)
                    self.graph.add_edge(class_node.id, method_node.id, EdgeType.DEFINES)

            # Register top-level functions
            for fn_model in file_model.functions:
                fn_node = self.symbol_table.register_function(
                    fn_model,
                    file_node,
                    class_node=None,
                )
                self.graph.add_node(fn_node)
                self.graph.add_edge(file_node.id, fn_node.id, EdgeType.DEFINES)

        # Step 3: Resolve IMPORTS edges
        for file_model in analysis.files:
            rel_path = normalize_file_path(file_model.file_path, str(self.repo_path))
            file_node = self.symbol_table.file_nodes.get(rel_path)
            if not file_node:
                continue

            current_module = file_node.properties.get("module_name", "")

            for imp in file_model.imports:
                raw_mod = imp.module or imp.name
                target_module = resolve_relative_module(raw_mod, current_module)

                # Check if target module maps to an internal repository file
                if target_module in self.symbol_table.module_to_file:
                    target_file_rel = self.symbol_table.module_to_file[target_module]
                    target_file_node = self.symbol_table.file_nodes.get(target_file_rel)
                    if target_file_node and target_file_node.id != file_node.id:
                        self.graph.add_edge(
                            file_node.id,
                            target_file_node.id,
                            EdgeType.IMPORTS,
                            imported_as=imp.imported_as,
                        )
                else:
                    # External module (e.g. fastapi, pydantic, os)
                    module_node_id = f"module::{target_module}"
                    if not self.graph.has_node(module_node_id):
                        self.graph.add_node(
                            Node(
                                id=module_node_id,
                                name=target_module,
                                type=NodeType.MODULE,
                                file_path="",
                            )
                        )
                    self.graph.add_edge(
                        file_node.id,
                        module_node_id,
                        EdgeType.IMPORTS,
                        imported_as=imp.imported_as,
                    )

        # Step 4: Resolve INHERITS edges
        for node in list(self.graph.nodes.values()):
            if node.type == NodeType.CLASS:
                for base_name in node.properties.get("base_classes", []):
                    base_node = self.symbol_table.resolve_inheritance(node, base_name)
                    if base_node:
                        self.graph.add_edge(
                            node.id,
                            base_node.id,
                            EdgeType.INHERITS,
                            base_name=base_name,
                        )

        # Step 5: Resolve CALLS edges
        for node in list(self.graph.nodes.values()):
            if node.type in (NodeType.FUNCTION, NodeType.METHOD):
                calls = node.properties.get("calls", [])
                for call_name in calls:
                    target_node, status, candidates = self.symbol_table.resolve_call(
                        node,
                        call_name,
                    )
                    if status == "resolved" and target_node:
                        self.graph.add_edge(
                            node.id,
                            target_node.id,
                            EdgeType.CALLS,
                            call_name=call_name,
                        )
                    elif status == "ambiguous":
                        self.graph.unresolved_calls.append(
                            UnresolvedCall(
                                caller_id=node.id,
                                call_name=call_name,
                                reason="ambiguous",
                                candidates=candidates,
                            )
                        )
                    else:
                        self.graph.unresolved_calls.append(
                            UnresolvedCall(
                                caller_id=node.id,
                                call_name=call_name,
                                reason="external_or_missing",
                                candidates=[],
                            )
                        )

        return self.graph


def build_code_graph(
    repo_path: Union[str, Path],
    ignored_directories: Optional[Set[str]] = None,
) -> CodeGraph:
    """Builds an in-memory CodeGraph representing all symbols, calls, and dependencies.

    Args:
        repo_path: Path to the repository directory.
        ignored_directories: Optional set of directory names to exclude during analysis.

    Returns:
        An indexed, queryable CodeGraph.
    """
    builder = GraphBuilder(repo_path=repo_path, ignored_directories=ignored_directories)
    return builder.build()
