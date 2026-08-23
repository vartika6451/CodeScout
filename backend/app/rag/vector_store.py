from app.services.database import get_connection


def delete_repository_chunks(repository: str):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM code_chunks
                WHERE repository = %s
                """,
                (repository,),
            )

        connection.commit()


def store_chunks(
    repository: str,
    chunks: list[dict],
    embeddings: list[list[float]],
):
    if len(chunks) != len(embeddings):
        raise ValueError(
            "Number of chunks must match number of embeddings"
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:

            for chunk, embedding in zip(chunks, embeddings):

                cursor.execute(
                    """
                    INSERT INTO code_chunks
                    (
                        repository,
                        file_path,
                        content,
                        chunk_index,
                        embedding
                    )
                    VALUES (%s, %s, %s, %s, %s::vector)
                    """,
                    (
                        repository,
                        chunk["file_path"],
                        chunk["content"],
                        chunk["chunk_index"],
                        str(embedding),
                    ),
                )

        connection.commit()