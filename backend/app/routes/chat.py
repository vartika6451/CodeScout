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
            "answer": result["answer"],
            "sources": [
                {
                    "file_path": chunk["file_path"],
                    "chunk_index": chunk["chunk_index"],
                    "similarity": chunk["similarity"],
                }
                for chunk in result["retrieved_chunks"]
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )