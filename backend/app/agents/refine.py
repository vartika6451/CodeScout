import os

from dotenv import load_dotenv
from google import genai

from app.agents.state import CodeScoutState


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def refine_query(state: CodeScoutState) -> CodeScoutState:
    """
    Rewrite the user's question to improve code retrieval.
    """

    question = state["question"]
    retrieved_chunks = state.get("retrieved_chunks", [])

    current_context = "\n\n".join(
        chunk["content"]
        for chunk in retrieved_chunks
    )

    prompt = f"""
You are helping an AI code analysis system improve its search query.

The user asked:

{question}

The retrieved code was:

{current_context}

The retrieved results were not relevant enough.

Rewrite the user's question into a more precise
technical search query that is likely to find
the correct code in the repository.

Return ONLY the rewritten search query.
Do not explain your answer.
"""

    response = client.models.generate_content(
        model=os.getenv(
            "GEMINI_MODEL",
            "gemini-3.7-flash"
        ).strip(),
        contents=prompt,
    )

    refined_question = response.text.strip()

    return {
        **state,
        "refined_question": refined_question,
    }