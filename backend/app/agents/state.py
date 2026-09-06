from typing import Any, Dict, List, Optional, TypedDict


class CodeScoutState(TypedDict, total=False):
    """The central state of the CodeScout agent throughout investigation and answer generation."""

    # Input specifications
    question: str
    repository: str

    # Legacy & RAG pipeline state
    retrieved_chunks: List[Dict[str, Any]]
    context: str
    answer: str
    needs_refinement: bool
    refined_question: str
    attempt_count: int

    # Phase 2: Agent Tools & Code Graph Investigation
    tool_calls: List[Dict[str, Any]]
    evidence: List[str]
    graph_results: List[Dict[str, Any]]
    next_tool: Optional[Dict[str, Any]]
    investigation_step: int
    is_sufficient: bool