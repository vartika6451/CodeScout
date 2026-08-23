import os

from dotenv import load_dotenv
from google import genai


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not set")


client = genai.Client(api_key=api_key)


def generate_answer(
    question: str,
    context: str,
) -> str:

    prompt = f"""
You are CodeScout, an AI code analysis assistant.

Answer the user's question using ONLY the provided
repository context.

If the answer cannot be found in the context,
say that you could not find enough information
in the repository.

Be concise but explain the relevant files and code.

USER QUESTION:
{question}

REPOSITORY CONTEXT:
{context}
"""

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip(),
        contents=prompt,
    )

    return response.text