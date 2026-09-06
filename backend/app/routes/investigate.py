from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.investigation import bug_investigation_graph

router = APIRouter()


class InvestigateRequest(BaseModel):
    repository: str
    bug_report: str
    repo_path: Optional[str] = None


@router.post("/investigate")
async def investigate_bug(request: InvestigateRequest):
    """Investigates a reported bug systematically using CodeGraph and RAG evidence."""
    try:
        initial_state = {
            "bug_report": request.bug_report,
            "repository": request.repository,
            "repo_path": request.repo_path,
        }

        result = bug_investigation_graph.invoke(initial_state)
        return result.get("final_report", {})

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
