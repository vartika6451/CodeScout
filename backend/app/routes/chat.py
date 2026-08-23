from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.rag.embeddings import create_embedding
from app.rag.retriever import search_similar_chunks
from app.rag.generator import generate_answer


router = APIRouter()


class ChatRequest(BaseModel):
    repository: str
    question: str


@router.post("/chat")
async def chat(request: ChatRequest):

    try:
        # 1. Convert the user's question into an embedding
        query_embedding = create_embedding(request.question)

        # 2. Find the most relevant code chunks
        results = search_similar_chunks(
            repository=request.repository,
            query_embedding=query_embedding,
            limit=5,
        )

        # 3. Make sure we found something
        if not results:
            raise HTTPException(
                status_code=404,
                detail="No relevant code found for this repository",
            )

        # 4. Build context for Gemini
        context_parts = []

        for result in results:

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

        # 5. Ask Gemini to answer using the retrieved code
        answer = generate_answer(
            question=request.question,
            context=context,
        )

        # 6. Return the answer + sources
        return {
            "answer": answer,
            "sources": [
                {
                    "file_path": result["file_path"],
                    "chunk_index": result["chunk_index"],
                    "similarity": result["similarity"],
                }
                for result in results
            ],
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )