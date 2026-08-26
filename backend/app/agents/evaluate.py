from app.agents.state import CodeScoutState


MAX_ATTEMPTS = 3


def evaluate_retrieval(state: CodeScoutState) -> CodeScoutState:
    """
    Check whether the retrieved chunks are relevant enough.
    """

    chunks = state.get("retrieved_chunks", [])

    attempt_count = state.get("attempt_count", 0)

    # Nothing was retrieved
    if not chunks:

        if attempt_count >= MAX_ATTEMPTS:
            return {
                **state,
                "needs_refinement": False,
            }

        return {
            **state,
            "needs_refinement": True,
        }

    # Get the strongest similarity score
    best_similarity = max(
        chunk["similarity"]
        for chunk in chunks
    )

    # Check whether retrieval is good enough
    needs_refinement = best_similarity < 0.60

    # Stop retrying after the maximum number of attempts
    if attempt_count >= MAX_ATTEMPTS:
        needs_refinement = False

    return {
        **state,
        "needs_refinement": needs_refinement,
    }