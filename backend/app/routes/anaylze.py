from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.github_service import get_repository

router = APIRouter()


class AnalyzeRequest(BaseModel):
    repo_url: str


@router.post("/analyze")
async def analyze_repository(request: AnalyzeRequest):
    try:
        parts = request.repo_url.rstrip("/").split("/")

        owner = parts[-2]
        repo = parts[-1]

        repository = await get_repository(owner, repo)

        return {
            "name": repository["name"],
            "owner": repository["owner"]["login"],
            "description": repository["description"],
            "stars": repository["stargazers_count"],
            "language": repository["language"],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))