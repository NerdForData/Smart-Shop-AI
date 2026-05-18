# rag/vector_store.py

import os
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from rag.bigquery_connector import query_bigquery, PROJECT_ID, DATASET_ID

load_dotenv()

CHROMA_DIR     = os.getenv("CHROMA_DIR", "./chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


def get_embeddings():
    """Load HuggingFace embeddings — free, no API key needed."""
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )


def build_product_vector_store():
    """
    Pull products from BigQuery and embed them
    into ChromaDB for semantic search by agents.
    """
    print("Fetching products from BigQuery...")

    sql = f"""
        SELECT name, category, price, description
        FROM `{PROJECT_ID}.{DATASET_ID}.products`
        LIMIT 5000
    """
    df = query_bigquery(sql)

    if df.empty:
        raise RuntimeError(
            "No products returned from BigQuery. "
            "Check that the products table has data."
        )

    print(f"Fetched {len(df)} products from BigQuery.")
    print("Embedding into ChromaDB — this may take a few minutes...")

    # Convert rows to LangChain Documents
    docs = [
        Document(
            page_content=row["description"],
            metadata={
                "name":     str(row["name"]),
                "category": str(row["category"]),
                "price":    float(row["price"])
            }
        )
        for _, row in df.iterrows()
    ]

    # Create and persist vector store
    embeddings   = get_embeddings()
    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    vector_store.persist()

    print(f"Vector store built and saved to {CHROMA_DIR}!")
    print(f"Total documents embedded: {len(docs)}")
    return vector_store


def load_vector_store():
    """Load existing vector store from disk."""
    if not os.path.exists(CHROMA_DIR):
        raise RuntimeError(
            f"ChromaDB not found at {CHROMA_DIR}. "
            "Run build_product_vector_store() first."
        )
    embeddings = get_embeddings()
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )


if __name__ == "__main__":
    print("=" * 50)
    print("  Building Product Vector Store")
    print("=" * 50)

    # Step 1: Build vector store from BigQuery data
    vector_store = build_product_vector_store()

    # Step 2: Test semantic search
    print("\nTesting semantic search...")

    test_queries = [
        "comfortable running shoes",
        "smartwatch with health tracking",
        "cheap electronics under $20"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = vector_store.similarity_search(query, k=3)
        for r in results:
            print(f"  → {r.metadata['name']} | "
                  f"{r.metadata['category']} | "
                  f"${r.metadata['price']:.2f}")

    print("\n" + "=" * 50)
    print("  Vector store ready!")
    print("=" * 50)