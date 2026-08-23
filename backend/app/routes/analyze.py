from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.rag.vector_store import (
    delete_repository_chunks,
    store_chunks,
)

from app.services.github_service import (
    get_repository,
    get_repository_tree,
    get_file_content,
)

from app.services.file_filter import should_analyze_file

from app.rag.chunker import chunk_code
from app.rag.embeddings import create_embeddings
from app.rag.vector_store import store_chunks


router = APIRouter()


class AnalyzeRequest(BaseModel):
    repo_url: str


@router.post("/analyze")
async def analyze_repository(request: AnalyzeRequest):

    try:
        # -----------------------------------
        # 1. Extract owner and repository name
        # -----------------------------------

        parts = request.repo_url.rstrip("/").split("/")

        if len(parts) < 2:
            raise ValueError("Invalid GitHub repository URL")

        owner = parts[-2]
        repo = parts[-1]

        repository_name = f"{owner}/{repo}"


        # -----------------------------------
        # 2. Get repository information
        # -----------------------------------

        repository = await get_repository(owner, repo)


        # -----------------------------------
        # 3. Get repository file tree
        # -----------------------------------

        tree = await get_repository_tree(owner, repo)


        # -----------------------------------
        # 4. Filter files
        # -----------------------------------

        files = [
            item["path"]
            for item in tree["tree"]
            if item["type"] == "blob"
            and should_analyze_file(item["path"])
        ]


        # -----------------------------------
        # 5. Fetch and chunk source code
        # -----------------------------------

        source_chunks = []

        for path in files:

            try:
                content = await get_file_content(
                    owner,
                    repo,
                    path
                )

                chunks = chunk_code(
                    path,
                    content
                )

                source_chunks.extend(chunks)

            except Exception as e:
                print(
                    f"Skipping {path}: {e}"
                )
                continue


        # -----------------------------------
        # 6. Make sure we have chunks
        # -----------------------------------

        if not source_chunks:
            raise ValueError(
                "No analyzable source code found"
            )


        # -----------------------------------
        # 7. Generate embeddings
        # -----------------------------------

        texts = [
            chunk["content"]
            for chunk in source_chunks
        ]

        embeddings = create_embeddings(texts)

        delete_repository_chunks(repository_name)


        # -----------------------------------
        # 8. Store chunks + embeddings
        # -----------------------------------

        store_chunks(
            repository=repository_name,
            chunks=source_chunks,
            embeddings=embeddings,
        )

        # -----------------------------------
        # 9. Return analysis information
        # -----------------------------------

        return {
            "message": "Repository analyzed successfully",
            "repository": repository["name"],
            "owner": repository["owner"]["login"],
            "language": repository["language"],
            "stars": repository["stargazers_count"],
            "total_files": len(files),
            "total_chunks": len(source_chunks),
            "embeddings_created": len(embeddings),
        }


    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )