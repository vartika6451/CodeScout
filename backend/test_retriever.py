from app.rag.embeddings import create_embedding
from app.rag.retriever import search_similar_chunks


query = "Where is user authentication implemented?"

query_embedding = create_embedding(query)

results = search_similar_chunks(
    repository="vartika6451/Yumzo",
    query_embedding=query_embedding,
    limit=5,
)


for result in results:
    print("\n----------------------------")
    print("File:", result["file_path"])
    print("Chunk:", result["chunk_index"])
    print("Similarity:", result["similarity"])
    print("Content:")
    print(result["content"])