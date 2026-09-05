from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.graph import code_scout_graph


router = APIRouter()


class ChatRequest(BaseModel):
    repository: str
    question: str


@router.post("/chat")
async def chat(request: ChatRequest):

    try:
        initial_state = {
            "repository": request.repository,
            "question": request.question,
        }

        result = code_scout_graph.invoke(initial_state)

        return {
            "answer": result.get("answer", ""),
            "sources": [
                {
                    "file_path": chunk.get("file_path", ""),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "similarity": round(float(chunk.get("similarity", 0)), 4),
                    "content": chunk.get("content", ""),
                }
                for chunk in result.get("retrieved_chunks", [])
            ],
            "refined_question": result.get("refined_question"),
            "attempt_count": result.get("attempt_count", 1),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )