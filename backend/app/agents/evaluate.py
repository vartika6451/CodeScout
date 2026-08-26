import json
import os

from dotenv import load_dotenv
from google import genai

from app.agents.state import CodeScoutState


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MAX_ATTEMPTS = 3


def evaluate_retrieval(state: CodeScoutState) -> CodeScoutState:
    """
    Use Gemini to determine whether the retrieved code
    is relevant to the user's question.
    """

    chunks = state.get("retrieved_chunks", [])
    attempt_count = state.get("attempt_count", 0)

    # Nothing was retrieved
    if not chunks:
        return {
            **state,
            "needs_refinement": attempt_count < MAX_ATTEMPTS,
        }

    question = state["question"]

    context = "\n\n".join(
        f"""
FILE: {chunk['file_path']}
CODE:
{chunk['content']}
"""
        for chunk in chunks
    )

    prompt = f"""
You are evaluating search results for an AI code analysis system.

USER QUESTION:
{question}

RETRIEVED CODE:
{context}

Determine whether the retrieved code is relevant enough
to answer the user's question.

Return ONLY valid JSON in this exact format:

{{
    "relevant": true
}}

or:

{{
    "relevant": false
}}

Do not include markdown.
Do not include explanations.
"""

    response = client.models.generate_content(
        model=os.getenv(
            "GEMINI_MODEL",
            "gemini-3.7-flash"
        ).strip(),
        contents=prompt,
    )

    try:
        evaluation = json.loads(response.text.strip())
        relevant = bool(evaluation.get("relevant", False))

    except (json.JSONDecodeError, AttributeError):
        # If Gemini returns something unexpected,
        # fall back to the similarity score.
        best_similarity = max(
            chunk["similarity"]
            for chunk in chunks
        )

        relevant = best_similarity >= 0.60

    needs_refinement = not relevant

    # Never allow infinite retries
    if attempt_count >= MAX_ATTEMPTS:
        needs_refinement = False

    return {
        **state,
        "needs_refinement": needs_refinement,
    }