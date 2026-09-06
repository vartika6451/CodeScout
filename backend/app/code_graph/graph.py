from typing import Any, Dict, List, Optional, Set, Tuple

from app.code_graph.models import Edge, EdgeType, Node, NodeType, UnresolvedCall


class CodeGraph:
    """An in-memory, navigable code dependency and call graph."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._outgoing: Dict[str, List[Edge]] = {}
        self._incoming: Dict[str, List[Edge]] = {}
        self._edge_keys: Set[Tuple[str, str, EdgeType]] = set()

        # Telemetry & unresolvable call audit tracking
        self.unresolved_calls: List[UnresolvedCall] = []

        # Secondary indexes for fast symbol resolution by name
        self._nodes_by_name: Dict[str, List[Node]] = {}
        self._nodes_by_file: Dict[str, List[Node]] = {}

    def add_node(self, node: Node) -> None:
        """Adds a node to the graph and indexes it."""
        self.nodes[node.id] = node

        # Index by simple name
        if node.name not in self._nodes_by_name:
            self._nodes_by_name[node.name] = []
        if node not in self._nodes_by_name[node.name]:
            self._nodes_by_name[node.name].append(node)

        # Index by file path
        if node.file_path:
            if node.file_path not in self._nodes_by_file:
                self._nodes_by_file[node.file_path] = []
            if node not in self._nodes_by_file[node.file_path]:
                self._nodes_by_file[node.file_path].append(node)

    def get_node(self, node_id: str) -> Optional[Node]:
        """Returns the node with the given ID, or None if not found."""
        return self.nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """Returns True if a node with the given ID exists."""
        return node_id in self.nodes

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        **properties: Any,
    ) -> Optional[Edge]:
        """Adds a directed relationship between two nodes if both nodes exist and edge is not duplicate."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        key = (source_id, target_id, edge_type)
        if key in self._edge_keys:
            return None

        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            type=edge_type,
            properties=properties,
        )

        self.edges.append(edge)
        self._edge_keys.add(key)

        self._outgoing.setdefault(source_id, []).append(edge)
        self._incoming.setdefault(target_id, []).append(edge)

        return edge

    def get_edges(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        edge_type: Optional[EdgeType] = None,
    ) -> List[Edge]:
        """Queries edges filtered by source ID, target ID, and/or relationship type."""
        candidate_edges = self.edges
        if source_id is not None:
            candidate_edges = self._outgoing.get(source_id, [])
        elif target_id is not None:
            candidate_edges = self._incoming.get(target_id, [])

        results: List[Edge] = []
        for e in candidate_edges:
            if source_id is not None and e.source_id != source_id:
                continue
            if target_id is not None and e.target_id != target_id:
                continue
            if edge_type is not None and e.type != edge_type:
                continue
            results.append(e)

        return results

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "outgoing",
        edge_type: Optional[EdgeType] = None,
    ) -> List[Node]:
        """Returns adjacent nodes along outgoing or incoming edges of an optional type."""
        if direction == "outgoing":
            edges = self._outgoing.get(node_id, [])
            neighbor_ids = [e.target_id for e in edges if edge_type is None or e.type == edge_type]
        else:
            edges = self._incoming.get(node_id, [])
            neighbor_ids = [e.source_id for e in edges if edge_type is None or e.type == edge_type]

        return [self.nodes[nid] for nid in neighbor_ids if nid in self.nodes]

    def _resolve_symbol_node(self, symbol: str) -> Optional[Node]:
        """Finds a node by exact ID, qualified suffix, or unique simple name."""
        if symbol in self.nodes:
            return self.nodes[symbol]

        # Check by qualified identifier ending with symbol
        # e.g., 'AuthService.login' or 'app.services.auth::AuthService.login'
        for node_id, node in self.nodes.items():
            if node_id.endswith(symbol):
                return node

        # Check by simple name if unambiguous
        candidates = self._nodes_by_name.get(symbol, [])
        if len(candidates) == 1:
            return candidates[0]

        return None

    def get_definition(self, symbol: str) -> Optional[Node]:
        """Finds the definition node for a symbol name, qualified name, or node ID."""
        return self._resolve_symbol_node(symbol)

    def get_callees(self, symbol: str) -> List[Node]:
        """Returns functions or methods that the specified function/method calls."""
        node = self._resolve_symbol_node(symbol)
        if not node:
            return []
        return self.get_neighbors(node.id, direction="outgoing", edge_type=EdgeType.CALLS)

    def get_callers(self, symbol: str) -> List[Node]:
        """Returns functions or methods that call the specified function/method."""
        node = self._resolve_symbol_node(symbol)
        if not node:
            return []
        return self.get_neighbors(node.id, direction="incoming", edge_type=EdgeType.CALLS)

    def get_class_methods(self, class_name_or_id: str) -> List[Node]:
        """Returns all methods defined by the specified class."""
        node = self._resolve_symbol_node(class_name_or_id)
        if not node or node.type != NodeType.CLASS:
            return []
        return self.get_neighbors(node.id, direction="outgoing", edge_type=EdgeType.DEFINES)

    def get_base_classes(self, class_name_or_id: str) -> List[Node]:
        """Returns classes that the specified class inherits from."""
        node = self._resolve_symbol_node(class_name_or_id)
        if not node or node.type != NodeType.CLASS:
            return []
        return self.get_neighbors(node.id, direction="outgoing", edge_type=EdgeType.INHERITS)

    def get_subclasses(self, class_name_or_id: str) -> List[Node]:
        """Returns classes that inherit from the specified class."""
        node = self._resolve_symbol_node(class_name_or_id)
        if not node or node.type != NodeType.CLASS:
            return []
        return self.get_neighbors(node.id, direction="incoming", edge_type=EdgeType.INHERITS)

    def get_file_symbols(self, file_path: str) -> List[Node]:
        """Returns all classes, functions, and methods defined in the specified file."""
        # Match exact file path or suffix
        matching_nodes: List[Node] = []
        for path, nodes in self._nodes_by_file.items():
            if path == file_path or path.endswith(file_path):
                matching_nodes.extend([n for n in nodes if n.type != NodeType.FILE])

        return matching_nodes

    def summary(self) -> Dict[str, Any]:
        """Produces a structured statistical summary of the code graph."""
        files = [n for n in self.nodes.values() if n.type == NodeType.FILE]
        classes = [n for n in self.nodes.values() if n.type == NodeType.CLASS]
        functions = [n for n in self.nodes.values() if n.type == NodeType.FUNCTION]
        methods = [n for n in self.nodes.values() if n.type == NodeType.METHOD]

        def_edges = [e for e in self.edges if e.type == EdgeType.DEFINES]
        call_edges = [e for e in self.edges if e.type == EdgeType.CALLS]
        import_edges = [e for e in self.edges if e.type == EdgeType.IMPORTS]
        inherits_edges = [e for e in self.edges if e.type == EdgeType.INHERITS]

        ambiguous_calls = [c for c in self.unresolved_calls if c.reason == "ambiguous"]
        external_calls = [c for c in self.unresolved_calls if c.reason != "ambiguous"]

        return {
            "files": len(files),
            "classes": len(classes),
            "functions": len(functions),
            "methods": len(methods),
            "definition_edges": len(def_edges),
            "call_edges": len(call_edges),
            "import_edges": len(import_edges),
            "inheritance_edges": len(inherits_edges),
            "resolved_calls": len(call_edges),
            "unresolved_calls": len(self.unresolved_calls),
            "ambiguous_calls": len(ambiguous_calls),
            "external_or_missing_calls": len(external_calls),
        }
