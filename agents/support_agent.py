# agents/support_agent.py

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix module path so 'rag' is always found
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Set Google API key before importing ADK
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
    get_order_by_id,
    get_customer_orders,
    search_products,
    query_bigquery,
    PROJECT_ID,
    DATASET_ID
)


# ── Tool Functions ─────────────────────────────────

def lookup_order(order_id: str) -> dict:
    """Look up a real order from BigQuery by order ID."""
    return get_order_by_id(order_id)


def get_my_orders(customer_id: str) -> list:
    """Get all orders for a customer from BigQuery."""
    return get_customer_orders(customer_id)


def search_for_product(keyword: str) -> list:
    """Search real product catalog from BigQuery."""
    return search_products(keyword)


# ── Agent Definition ───────────────────────────────

support_agent = Agent(
    name="support_agent",
    model="gemini-2.0-flash-lite",
    description="Handles customer support using real order and product data",
    instruction="""You are a helpful SmartShop customer support agent.
    You have access to the REAL product catalog and order database.

    - For order questions: use lookup_order or get_my_orders
    - For product questions: use search_for_product
    - Always give specific, accurate answers based on the data
    - If an order is not found, say so clearly
    - Be friendly and professional""",
    tools=[lookup_order, get_my_orders, search_for_product]
)


# ── Test Runner ────────────────────────────────────

# ── Test Runner ────────────────────────────────────

async def test_agent():
    """Test the support agent with real questions."""

    session_service = InMemorySessionService()
    runner = Runner(
        agent=support_agent,
        app_name="smartshop_support",
        session_service=session_service
    )

    # ← add await here
    session = await session_service.create_session(
        app_name="smartshop_support",
        user_id="test_user"
    )

    test_questions = [
        "Do you have any watches available?",
        "I'm looking for cheap electronics",
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
    print("  SmartShop Support Agent")
    print("=" * 50)

    # Step 1: Verify tools work directly
    print("\n[TEST 1] Tool: search_for_product('watch')")
    try:
        results = search_for_product("watch")
        if results:
            for r in results[:2]:
                print(f"  → {r['name']} | ${r['price']:.2f}")
        else:
            print("  ⚠ No results found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    print("\n[TEST 2] Tool: lookup_order (real order from DB)")
    try:
        sample = query_bigquery(
            f"SELECT order_id, customer_id "
            f"FROM `{PROJECT_ID}.{DATASET_ID}.orders` LIMIT 1"
        )
        if not sample.empty:
            order_id    = sample.iloc[0]["order_id"]
            customer_id = sample.iloc[0]["customer_id"]

            order = lookup_order(order_id)
            print(f"  Order ID : {order.get('order_id')}")
            print(f"  Status   : {order.get('order_status')}")
            print(f"  Amount   : ${float(order.get('total_amount', 0)):.2f}")

            orders = get_my_orders(customer_id)
            print(f"  Customer orders: {len(orders)}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Step 2: Run agent with real questions
    print("\n[TEST 3] Running agent with Gemini...")
    asyncio.run(test_agent())

    print("\n" + "=" * 50)
    print("  Support agent ready!")
    print("=" * 50)