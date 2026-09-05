from fastapi import APIRouter, HTTPException
from app.services.database import get_connection
from app.rag.vector_store import delete_repository_chunks

router = APIRouter()


@router.get("/repositories")
async def list_repositories():
    """
    List all repositories indexed in the vector store along with chunk and file counts.
    """
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        repository, 
                        COUNT(*) AS total_chunks,
                        COUNT(DISTINCT file_path) AS total_files
                    FROM code_chunks
                    GROUP BY repository
                    ORDER BY repository ASC;
                    """
                )
                rows = cursor.fetchall()

        repositories = [
            {
                "repository": row[0],
                "total_chunks": row[1],
                "total_files": row[2],
            }
            for row in rows
        ]

        return {"repositories": repositories}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch repositories: {str(e)}",
        )


@router.delete("/repositories/{owner}/{repo}")
async def delete_repository(owner: str, repo: str):
    """
    Delete all indexed chunks for a given repository.
    """
    repository_name = f"{owner}/{repo}"
    try:
        delete_repository_chunks(repository_name)
        return {
            "message": f"Successfully deleted vectors for repository '{repository_name}'",
            "repository": repository_name,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete repository chunks: {str(e)}",
        )
