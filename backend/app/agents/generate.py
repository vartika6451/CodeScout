from app.agents.state import CodeScoutState
from app.rag.generator import generate_answer


def generate_node(state: CodeScoutState) -> CodeScoutState:
    """
    Generate an answer using the retrieved repository context.
    """

    question = state["question"]
    retrieved_chunks = state["retrieved_chunks"]

    # Build context from retrieved code chunks
    context_parts = []

    for result in retrieved_chunks:
        context_parts.append(
            f"""
FILE: {result['file_path']}
CHUNK: {result['chunk_index']}
SIMILARITY: {result['similarity']:.2f}

CODE:
{result['content']}
"""
        )

    context = "\n".join(context_parts)

    # Ask Gemini to generate the answer
    answer = generate_answer(
        question=question,
        context=context,
    )

    # Add context and answer to the state
    return {
        **state,
        "context": context,
        "answer": answer,
    }