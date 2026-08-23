from app.services.database import get_connection


def search_similar_chunks(
    repository: str,
    query_embedding: list[float],
    limit: int = 5,
):
    with get_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    file_path,
                    content,
                    chunk_index,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM code_chunks
                WHERE repository = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    str(query_embedding),
                    repository,
                    str(query_embedding),
                    limit,
                ),
            )

            rows = cursor.fetchall()

    return [
        {
            "file_path": row[0],
            "content": row[1],
            "chunk_index": row[2],
            "similarity": float(row[3]),
        }
        for row in rows
    ]