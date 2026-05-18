# agents/recommender_agent.py

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix module path so 'rag' is always found
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Set API key before importing ADK
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY not set. Add it to your .env file.\n"
        "Get a free key at: https://aistudio.google.com/apikey"
    )
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from rag.bigquery_connector import (
    get_products_by_category,
    get_product_stats,
    query_bigquery,
    PROJECT_ID,
    DATASET_ID
)
from rag.vector_store import load_vector_store

# Load vector store once at startup
print("Loading vector store...")
vector_store = load_vector_store()
print("Vector store loaded!")


# ── Tool Functions ─────────────────────────────────

def semantic_product_search(query: str) -> list:
    """Find products using semantic similarity search on real data."""
    results = vector_store.similarity_search(query, k=5)
    return [
        {
            "name":        doc.metadata["name"],
            "category":    doc.metadata["category"],
            "price":       doc.metadata["price"],
            "description": doc.page_content
        }
        for doc in results
    ]


def get_category_products(category: str, max_price: float) -> list:
    """Get real products from BigQuery by category and budget."""
    return get_products_by_category(category, max_price)


def get_catalog_overview() -> dict:
    """Get high-level stats about the product catalog."""
    return get_product_stats()


# ── Agent Definition ───────────────────────────────

recommender_agent = Agent(
    name="recommender_agent",
    model="gemini-2.0-flash-lite",
    description="Recommends real products from the live catalog",
    instruction="""You are a personal shopping assistant with access
    to a REAL product catalog sourced from BigQuery.

    - Use semantic_product_search for natural language queries
    - Use get_category_products when user specifies a category + budget
    - Use get_catalog_overview to understand what's available
    - Always mention real prices from the database
    - Explain WHY you are recommending each product""",
    tools=[semantic_product_search, get_category_products, get_catalog_overview]
)


# ── Test Runner ────────────────────────────────────

async def test_agent():
    """Test the recommender agent with real questions."""

    session_service = InMemorySessionService()
    runner = Runner(
        agent=recommender_agent,
        app_name="smartshop_recommender",
        session_service=session_service
    )

    session = await session_service.create_session(
        app_name="smartshop_recommender",
        user_id="test_user"
    )

    test_questions = [
        "I'm looking for a gift for someone who loves fitness",
        "Show me electronics under $50",
    ]

    for question in test_questions:
        print(f"\nUser: {question}")
        print("Agent: ", end="", flush=True)

        message = types.Content(
            role="user",
            parts=[types.Part(text=question)]
        )

        try:
            async for event in runner.run_async(
                user_id="test_user",
                session_id=session.id,
                new_message=message
            ):
                if event.is_final_response():
                    print(event.content.parts[0].text)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    import asyncio

    print("=" * 50)
    print("  SmartShop Recommender Agent")
    print("=" * 50)

    # Test 1: Semantic search directly
    print("\n[TEST 1] Semantic search: 'running shoes'")
    try:
        results = semantic_product_search("running shoes")
        if results:
            for r in results[:3]:
                print(f"  → {r['name']} | {r['category']} | ${r['price']:.2f}")
        else:
            print("  ⚠ No results found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 2: Category + price filter
    print("\n[TEST 2] Category products: 'electronics' under $50")
    try:
        results = get_category_products("electronics", 50.0)
        if results:
            for r in results[:3]:
                print(f"  → {r['name']} | ${r['price']:.2f}")
        else:
            print("  ⚠ No results found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 3: Catalog overview
    print("\n[TEST 3] Catalog overview")
    try:
        stats = get_catalog_overview()
        print(f"  Total products   : {int(stats['total_products'])}")
        print(f"  Avg price        : ${stats['avg_price']:.2f}")
        print(f"  Total categories : {int(stats['total_categories'])}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 4: Run agent with Gemini
    print("\n[TEST 4] Running agent with Gemini...")
    asyncio.run(test_agent())

    print("\n" + "=" * 50)
    print("  Recommender agent ready!")
    print("=" * 50)