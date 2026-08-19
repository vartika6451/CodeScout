from fastapi import APIRouter
from pydantic import BaseModel
# whenever someone calls /anaylze, I expect a request containing repo_url, and it must be a string

router = APIRouter()


class AnalyzeRequest(BaseModel):
    repo_url: str


@router.post("/analyze")
def analyze_repository(request: AnalyzeRequest):
    return {
        "message": "Repository received",
        "repo_url": request.repo_url
    }