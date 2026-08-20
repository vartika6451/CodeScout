from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.github_service import (
    get_repository,
    get_repository_tree,
    get_file_content,
)

from app.services.file_filter import should_analyze_file


router = APIRouter()


class AnalyzeRequest(BaseModel):
    repo_url: str


@router.post("/analyze")
async def analyze_repository(request: AnalyzeRequest):
    try:
        # Extract owner and repository name from GitHub URL
        parts = request.repo_url.rstrip("/").split("/")

        owner = parts[-2]
        repo = parts[-1]

        # Fetch repository information
        repository = await get_repository(owner, repo)

        # Fetch repository file tree
        tree = await get_repository_tree(owner, repo)

        # Keep only files that are useful for code analysis
        files = [
            item["path"]
            for item in tree["tree"]
            if item["type"] == "blob"
            and should_analyze_file(item["path"])
        ]

        # Fetch the actual source code
        source_files = []

        for path in files:
            try:
                content = await get_file_content(owner, repo, path)

                source_files.append({
                    "path": path,
                    "content": content,
                })

            except Exception:
                # Skip files that cannot be fetched
                continue

        return {
            "repository": repository["name"],
            "owner": repository["owner"]["login"],
            "language": repository["language"],
            "stars": repository["stargazers_count"],
            "files": source_files,
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )