from app.rag.embeddings import create_embedding
from app.rag.retriever import search_similar_chunks

from app.agents.state import CodeScoutState


def retrieve_node(state: CodeScoutState) -> CodeScoutState:
    """
    Retrieve the most relevant code chunks for the user's question.
    """

    question = state["question"]
    repository = state["repository"]

    # Convert the question into an embedding
    query_embedding = create_embedding(question)

    # Search pgvector for relevant code
    results = search_similar_chunks(
        repository=repository,
        query_embedding=query_embedding,
        limit=5,
    )

    # Store the results in the LangGraph state
    return {
        **state,
        "retrieved_chunks": results,
    }