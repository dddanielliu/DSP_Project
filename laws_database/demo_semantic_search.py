import os
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer

# ------------------ PostgreSQL Connection ------------------
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = os.environ.get("PG_PORT", "5432")
PG_DATABASE = os.environ.get("PG_DATABASE", "lawdb")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "postgres")

PG_CONN_STRING = (
    f"dbname={PG_DATABASE} user={PG_USER} password={PG_PASSWORD} "
    f"host={PG_HOST} port={PG_PORT}"
)

# ------------------ Load Embedding Model ------------------
MODEL_NAME = "intfloat/multilingual-e5-large"
model = SentenceTransformer(
    MODEL_NAME,
    tokenizer_kwargs={"padding_side": "left"},
)

# ------------------ Query Function ------------------
def query_top_k_law_chunks(query: str, top_k: int = 5):
    """Return top-k most relevant law chunks for a given query string."""
    # Compute embedding of the query
    query_embedding = model.encode([query])[0]
    print("embedding complete")
    print(query_embedding)
    embedding_str = str(query_embedding.tolist())  # convert to PostgreSQL array format

    # Connect to PostgreSQL
    conn = psycopg2.connect(PG_CONN_STRING)
    cur = conn.cursor()

    # pgvector similarity search using L2 (Euclidean distance)
    sql = f"""
    SELECT id, law_name, chapter, article_no, chunk_index, content, embedding
    FROM law_chunks
    ORDER BY embedding <-> %s::vector
    LIMIT %s;
    """
    cur.execute(sql, (embedding_str, top_k))
    results = cur.fetchall()

    cur.close()
    conn.close()

    return results

# ------------------ Demo ------------------
if __name__ == "__main__":
    query = input("Enter your query: ")
    top_chunks = query_top_k_law_chunks(query, top_k=5)

    print("\nTop 5 most relevant law chunks:")
    for i, chunk in enumerate(top_chunks, 1):
        print(f"\n#{i} | Law: {chunk[1]}, Chapter: {chunk[2]}, Article: {chunk[3]}, Chunk Index: {chunk[4]}")
        print(f"Content: {chunk[5][:300]}{'...' if len(chunk[5]) > 300 else ''}")

