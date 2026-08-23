from typing import TypedDict, List, Dict, Any


class CodeScoutState(TypedDict, total=False):
    question: str
    repository: str

    retrieved_chunks: List[Dict[str, Any]]

    context: str

    answer: str