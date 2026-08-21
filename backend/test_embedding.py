from app.rag.embeddings import create_embedding


text = """
This function authenticates a user using their email and password.
"""

embedding = create_embedding(text)

print("Embedding dimensions:", len(embedding))
print("First 10 values:", embedding[:10])