from typing import TypedDict, List, Dict, Any


class CodeScoutState(TypedDict, total=False):
    question: str
    repository: str

    retrieved_chunks: List[Dict[str, Any]]

    context: str

    answer: str

    needs_refinement: bool
    refined_question: str
    attempt_count: int