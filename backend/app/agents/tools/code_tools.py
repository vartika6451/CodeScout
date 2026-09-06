from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from app.code_graph import CodeGraph, EdgeType, Node, NodeType, build_code_graph

# In-memory graph cache to avoid rebuilding repeatedly during multi-turn investigations
_GRAPH_CACHE: Dict[str, CodeGraph] = {}


def get_repository_graph(repo_path: Optional[Union[str, Path]] = None) -> CodeGraph:
    """Retrieves or builds the CodeGraph for a repository path (cached)."""
    if repo_path is None:
        # Default to the backend directory or workspace root
        current_dir = Path(__file__).resolve().parent.parent.parent
        repo_path = current_dir if current_dir.name == "backend" else current_dir.parent

    resolved_path = str(Path(repo_path).resolve())
    if resolved_path not in _GRAPH_CACHE:
        _GRAPH_CACHE[resolved_path] = build_code_graph(resolved_path)
    return _GRAPH_CACHE[resolved_path]


def clear_graph_cache() -> None:
    """Clears the cached code graphs."""
    _GRAPH_CACHE.clear()


# ==============================================================================
# TOOL 1: Search Code (RAG)
# ==============================================================================
def search_code(
    query: str,
    repository: Optional[str] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Semantic vector search across repository code chunks using the existing RAG system."""
    try:
        from app.rag.embeddings import create_embedding
        from app.rag.retriever import search_similar_chunks

        query_embedding = create_embedding(query)
        chunks = search_similar_chunks(
            repository=repository or "",
            query_embedding=query_embedding,
            limit=top_k,
        )

        return {
            "success": True,
            "tool": "search_code",
            "query": query,
            "repository": repository,
            "results": [
                {
                    "file_path": c.get("file_path", ""),
                    "content": c.get("content", ""),
                    "chunk_index": c.get("chunk_index", 0),
                    "similarity": round(float(c.get("similarity", 0)), 4),
                }
                for c in chunks
            ],
            "count": len(chunks),
        }
    except Exception as exc:
        return {
            "success": False,
            "tool": "search_code",
            "query": query,
            "error": f"Semantic search failed: {str(exc)}",
            "results": [],
            "count": 0,
        }


# ==============================================================================
# TOOL 2: Find Symbol Definition
# ==============================================================================
def find_definition(
    symbol: str,
    repo_path: Optional[Union[str, Path]] = None,
    graph: Optional[CodeGraph] = None,
) -> Dict[str, Any]:
    """Locates the exact definition location, line numbers, and metadata of a symbol."""
    g = graph or get_repository_graph(repo_path)
    node = g.get_definition(symbol)

    if not node:
        return {
            "success": False,
            "tool": "find_definition",
            "symbol": symbol,
            "error": f"Symbol '{symbol}' not found in codebase",
        }

    return {
        "success": True,
        "tool": "find_definition",
        "symbol": symbol,
        "definition": {
            "id": node.id,
            "name": node.name,
            "type": node.type.value,
            "file_path": node.file_path,
            "line_number": node.line_number,
            "end_line_number": node.end_line_number,
            "properties": node.properties,
        },
    }


# ==============================================================================
# TOOL 3: Find Callees
# ==============================================================================
def find_callees(
    symbol: str,
    repo_path: Optional[Union[str, Path]] = None,
    graph: Optional[CodeGraph] = None,
) -> Dict[str, Any]:
    """Finds all functions or methods directly called by the specified symbol."""
    g = graph or get_repository_graph(repo_path)
    node = g.get_definition(symbol)

    if not node:
        return {
            "success": False,
            "tool": "find_callees",
            "symbol": symbol,
            "error": f"Symbol '{symbol}' not found in codebase",
            "callees": [],
        }

    callees = g.get_callees(node.id)
    return {
        "success": True,
        "tool": "find_callees",
        "symbol": symbol,
        "caller": {
            "id": node.id,
            "name": node.name,
            "type": node.type.value,
            "file_path": node.file_path,
            "line_number": node.line_number,
        },
        "callees": [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type.value,
                "file_path": c.file_path,
                "line_number": c.line_number,
            }
            for c in callees
        ],
        "count": len(callees),
    }


# ==============================================================================
# TOOL 4: Find Callers
# ==============================================================================
def find_callers(
    symbol: str,
    repo_path: Optional[Union[str, Path]] = None,
    graph: Optional[CodeGraph] = None,
) -> Dict[str, Any]:
    """Finds all functions or methods that call the specified symbol."""
    g = graph or get_repository_graph(repo_path)
    node = g.get_definition(symbol)

    if not node:
        return {
            "success": False,
            "tool": "find_callers",
            "symbol": symbol,
            "error": f"Symbol '{symbol}' not found in codebase",
            "callers": [],
        }

    callers = g.get_callers(node.id)
    return {
        "success": True,
        "tool": "find_callers",
        "symbol": symbol,
        "target": {
            "id": node.id,
            "name": node.name,
            "type": node.type.value,
            "file_path": node.file_path,
            "line_number": node.line_number,
        },
        "callers": [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type.value,
                "file_path": c.file_path,
                "line_number": c.line_number,
            }
            for c in callers
        ],
        "count": len(callers),
    }


# ==============================================================================
# TOOL 5: Find References
# ==============================================================================
def find_references(
    symbol: str,
    repo_path: Optional[Union[str, Path]] = None,
    graph: Optional[CodeGraph] = None,
) -> Dict[str, Any]:
    """Finds definitions and cross-references (call sites, imports, subclasses) for a symbol."""
    g = graph or get_repository_graph(repo_path)
    def_node = g.get_definition(symbol)

    callers = g.get_callers(def_node.id if def_node else symbol)

    # Find import sites: files that import this symbol or its module
    import_sites: List[Dict[str, Any]] = []
    if def_node:
        module_name = def_node.properties.get("module_name", "")
        for edge in g.edges:
            if edge.type == EdgeType.IMPORTS:
                imported = edge.properties.get("imported_as")
                if imported == def_node.name or (module_name and edge.target_id.endswith(module_name)):
                    source_node = g.get_node(edge.source_id)
                    if source_node:
                        import_sites.append({
                            "file_path": source_node.file_path,
                            "file_id": source_node.id,
                            "imported_as": imported,
                        })

    # Find subclasses if symbol is a class
    subclasses: List[Dict[str, Any]] = []
    if def_node and def_node.type == NodeType.CLASS:
        for sub in g.get_subclasses(def_node.id):
            subclasses.append({
                "id": sub.id,
                "name": sub.name,
                "file_path": sub.file_path,
                "line_number": sub.line_number,
            })

    total_refs = len(callers) + len(import_sites) + len(subclasses)

    if not def_node and total_refs == 0:
        return {
            "success": False,
            "tool": "find_references",
            "symbol": symbol,
            "error": f"Symbol '{symbol}' not found and has no references",
            "references": {},
        }

    return {
        "success": True,
        "tool": "find_references",
        "symbol": symbol,
        "definition": {
            "id": def_node.id,
            "type": def_node.type.value,
            "file_path": def_node.file_path,
            "line_number": def_node.line_number,
        } if def_node else None,
        "references": {
            "call_sites": [
                {
                    "id": c.id,
                    "name": c.name,
                    "type": c.type.value,
                    "file_path": c.file_path,
                    "line_number": c.line_number,
                }
                for c in callers
            ],
            "import_sites": import_sites,
            "subclasses": subclasses,
        },
        "total_references": total_refs,
    }


# ==============================================================================
# TOOL 6: Get File Structure
# ==============================================================================
def get_file_structure(
    file_path: str,
    repo_path: Optional[Union[str, Path]] = None,
    graph: Optional[CodeGraph] = None,
) -> Dict[str, Any]:
    """Returns the structural outline (classes, methods, functions, imports) of a file."""
    g = graph or get_repository_graph(repo_path)

    # Match exact or suffix
    file_node: Optional[Node] = None
    for n in g.nodes.values():
        if n.type == NodeType.FILE and (n.file_path == file_path or n.file_path.endswith(file_path)):
            file_node = n
            break

    if not file_node:
        return {
            "success": False,
            "tool": "get_file_structure",
            "file_path": file_path,
            "error": f"File '{file_path}' not found in codebase",
        }

    symbols = g.get_file_symbols(file_node.file_path)
    classes = [s for s in symbols if s.type == NodeType.CLASS]
    functions = [s for s in symbols if s.type == NodeType.FUNCTION]

    # Outgoing imports from this file
    import_edges = g.get_edges(source_id=file_node.id, edge_type=EdgeType.IMPORTS)
    imported = []
    for edge in import_edges:
        target_node = g.get_node(edge.target_id)
        imported.append({
            "target": target_node.name if target_node else edge.target_id,
            "type": target_node.type.value if target_node else "UNKNOWN",
            "imported_as": edge.properties.get("imported_as"),
        })

    return {
        "success": True,
        "tool": "get_file_structure",
        "file_path": file_node.file_path,
        "module_name": file_node.properties.get("module_name", ""),
        "imports": imported,
        "classes": [
            {
                "name": cls.name,
                "line_number": cls.line_number,
                "base_classes": cls.properties.get("base_classes", []),
                "methods": [
                    {
                        "name": m.name,
                        "line_number": m.line_number,
                        "is_async": m.properties.get("is_async", False),
                        "calls": m.properties.get("calls", []),
                    }
                    for m in g.get_class_methods(cls.id)
                ],
            }
            for cls in classes
        ],
        "functions": [
            {
                "name": fn.name,
                "line_number": fn.line_number,
                "is_async": fn.properties.get("is_async", False),
                "calls": fn.properties.get("calls", []),
            }
            for fn in functions
        ],
    }


# ==============================================================================
# TOOL 7: Get Class Information
# ==============================================================================
def get_class_info(
    class_name: str,
    repo_path: Optional[Union[str, Path]] = None,
    graph: Optional[CodeGraph] = None,
) -> Dict[str, Any]:
    """Retrieves class details: methods, inheritance base classes, and subclasses."""
    g = graph or get_repository_graph(repo_path)
    cls_node = g.get_definition(class_name)

    if not cls_node or cls_node.type != NodeType.CLASS:
        return {
            "success": False,
            "tool": "get_class_info",
            "class_name": class_name,
            "error": f"Class '{class_name}' not found in codebase",
        }

    methods = g.get_class_methods(cls_node.id)
    base_classes = g.get_base_classes(cls_node.id)
    subclasses = g.get_subclasses(cls_node.id)

    return {
        "success": True,
        "tool": "get_class_info",
        "class_name": cls_node.name,
        "id": cls_node.id,
        "file_path": cls_node.file_path,
        "line_number": cls_node.line_number,
        "methods": [
            {
                "name": m.name,
                "line_number": m.line_number,
                "is_async": m.properties.get("is_async", False),
                "calls": m.properties.get("calls", []),
            }
            for m in methods
        ],
        "base_classes": [b.name for b in base_classes] or cls_node.properties.get("base_classes", []),
        "subclasses": [
            {
                "name": s.name,
                "id": s.id,
                "file_path": s.file_path,
            }
            for s in subclasses
        ],
    }


# ==============================================================================
# TOOL 8: Trace Function (Call Tree with Cycle Protection)
# ==============================================================================
def trace_function(
    symbol: str,
    depth: int = 2,
    repo_path: Optional[Union[str, Path]] = None,
    graph: Optional[CodeGraph] = None,
) -> Dict[str, Any]:
    """Traces a function's call hierarchy up to a configured depth with cycle detection."""
    g = graph or get_repository_graph(repo_path)
    root_node = g.get_definition(symbol)

    if not root_node or root_node.type not in (NodeType.FUNCTION, NodeType.METHOD):
        return {
            "success": False,
            "tool": "trace_function",
            "symbol": symbol,
            "error": f"Function or method '{symbol}' not found in codebase",
        }

    def _build_call_tree(
        node: Node,
        current_depth: int,
        max_depth: int,
        path: Set[str],
    ) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "id": node.id,
            "name": node.name,
            "type": node.type.value,
            "file_path": node.file_path,
            "line_number": node.line_number,
            "depth": current_depth,
            "calls": [],
        }

        if current_depth >= max_depth:
            return info

        for callee in g.get_callees(node.id):
            if callee.id in path:
                # Cycle detected! Record cycle leaf without infinite recursion
                info["calls"].append({
                    "id": callee.id,
                    "name": callee.name,
                    "file_path": callee.file_path,
                    "line_number": callee.line_number,
                    "depth": current_depth + 1,
                    "is_cycle": True,
                    "calls": [],
                })
            else:
                child_tree = _build_call_tree(
                    callee,
                    current_depth + 1,
                    max_depth,
                    path | {callee.id},
                )
                info["calls"].append(child_tree)

        return info

    tree = _build_call_tree(
        node=root_node,
        current_depth=0,
        max_depth=depth,
        path={root_node.id},
    )

    return {
        "success": True,
        "tool": "trace_function",
        "root_symbol": symbol,
        "max_depth": depth,
        "tree": tree,
    }


# ==============================================================================
# TOOL 9: Get Dependencies
# ==============================================================================
def get_dependencies(
    file_or_symbol: str,
    repo_path: Optional[Union[str, Path]] = None,
    graph: Optional[CodeGraph] = None,
) -> Dict[str, Any]:
    """Identifies files, modules, or symbols that the target depends on."""
    g = graph or get_repository_graph(repo_path)

    # Check if target is a file
    file_node: Optional[Node] = None
    for n in g.nodes.values():
        if n.type == NodeType.FILE and (n.file_path == file_or_symbol or n.file_path.endswith(file_or_symbol)):
            file_node = n
            break

    if file_node:
        import_edges = g.get_edges(source_id=file_node.id, edge_type=EdgeType.IMPORTS)
        imported_files = []
        imported_modules = []
        for e in import_edges:
            target = g.get_node(e.target_id)
            if target and target.type == NodeType.FILE:
                imported_files.append(target.file_path)
            elif target and target.type == NodeType.MODULE:
                imported_modules.append(target.name)
            else:
                imported_modules.append(e.target_id)

        # Also find functions in other files called by functions in this file
        file_symbols = g.get_file_symbols(file_node.file_path)
        called_external_symbols = []
        for sym in file_symbols:
            for callee in g.get_callees(sym.id):
                if callee.file_path != file_node.file_path:
                    called_external_symbols.append({
                        "caller": sym.name,
                        "callee": callee.name,
                        "file_path": callee.file_path,
                        "line_number": callee.line_number,
                    })

        return {
            "success": True,
            "tool": "get_dependencies",
            "target": file_or_symbol,
            "target_type": "file",
            "imported_files": sorted(list(set(imported_files))),
            "imported_modules": sorted(list(set(imported_modules))),
            "called_external_symbols": called_external_symbols,
        }

    # Otherwise treat as symbol
    sym_node = g.get_definition(file_or_symbol)
    if not sym_node:
        return {
            "success": False,
            "tool": "get_dependencies",
            "target": file_or_symbol,
            "error": f"Target '{file_or_symbol}' not found as file or symbol",
        }

    callees = g.get_callees(sym_node.id)
    base_classes = g.get_base_classes(sym_node.id) if sym_node.type == NodeType.CLASS else []

    return {
        "success": True,
        "tool": "get_dependencies",
        "target": file_or_symbol,
        "target_type": sym_node.type.value.lower(),
        "callees": [
            {"name": c.name, "id": c.id, "file_path": c.file_path, "line_number": c.line_number}
            for c in callees
        ],
        "base_classes": [b.name for b in base_classes],
    }


# ==============================================================================
# TOOL 10: Get Dependents
# ==============================================================================
def get_dependents(
    file_or_symbol: str,
    repo_path: Optional[Union[str, Path]] = None,
    graph: Optional[CodeGraph] = None,
) -> Dict[str, Any]:
    """Identifies files or symbols that depend on the target (reverse dependencies)."""
    g = graph or get_repository_graph(repo_path)

    # Check if target is a file
    file_node: Optional[Node] = None
    for n in g.nodes.values():
        if n.type == NodeType.FILE and (n.file_path == file_or_symbol or n.file_path.endswith(file_or_symbol)):
            file_node = n
            break

    if file_node:
        # Files that import this file
        import_edges = g.get_edges(target_id=file_node.id, edge_type=EdgeType.IMPORTS)
        dependent_files = []
        for e in import_edges:
            source = g.get_node(e.source_id)
            if source:
                dependent_files.append(source.file_path)

        # Functions in other files calling functions in this file
        file_symbols = g.get_file_symbols(file_node.file_path)
        callers_from_other_files = []
        for sym in file_symbols:
            for caller in g.get_callers(sym.id):
                if caller.file_path != file_node.file_path:
                    callers_from_other_files.append({
                        "target_symbol": sym.name,
                        "caller_name": caller.name,
                        "file_path": caller.file_path,
                        "line_number": caller.line_number,
                    })

        return {
            "success": True,
            "tool": "get_dependents",
            "target": file_or_symbol,
            "target_type": "file",
            "dependent_files": sorted(list(set(dependent_files))),
            "external_callers": callers_from_other_files,
        }

    # Otherwise treat as symbol
    sym_node = g.get_definition(file_or_symbol)
    if not sym_node:
        return {
            "success": False,
            "tool": "get_dependents",
            "target": file_or_symbol,
            "error": f"Target '{file_or_symbol}' not found as file or symbol",
        }

    callers = g.get_callers(sym_node.id)
    subclasses = g.get_subclasses(sym_node.id) if sym_node.type == NodeType.CLASS else []

    return {
        "success": True,
        "tool": "get_dependents",
        "target": file_or_symbol,
        "target_type": sym_node.type.value.lower(),
        "callers": [
            {"name": c.name, "id": c.id, "file_path": c.file_path, "line_number": c.line_number}
            for c in callers
        ],
        "subclasses": [
            {"name": s.name, "id": s.id, "file_path": s.file_path}
            for s in subclasses
        ],
    }
