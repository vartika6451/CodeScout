import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not set")

client = genai.Client(api_key=api_key)


def create_embedding(text: str):
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )

    return response.embeddings[0].values


def create_embeddings(texts: list[str]):
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=texts,
    )

    return [embedding.values for embedding in response.embeddings]