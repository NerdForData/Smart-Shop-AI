# agents/fraud_agent.py

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
    analyze_transaction_risk,
    get_fraud_patterns,
    query_bigquery,
    PROJECT_ID,
    DATASET_ID
)


# ── Tool Functions ─────────────────────────────────

def check_transaction_risk(
    amount: float,
    category: str,
    state: str
) -> dict:
    """
    Analyze transaction risk against REAL historical
    fraud patterns stored in BigQuery.
    """
    return analyze_transaction_risk(amount, category, state)


def get_category_fraud_history(category: str) -> dict:
    """Get historical fraud statistics for a merchant category."""
    return get_fraud_patterns(category)


# ── Agent Definition ───────────────────────────────

fraud_agent = Agent(
    name="fraud_agent",
    model="gemini-2.0-flash-lite",
    description="Detects fraud using real historical transaction patterns",
    instruction="""You are a fraud detection specialist.
    You analyze transactions against REAL historical fraud data from BigQuery.

    - Use check_transaction_risk to score incoming transactions
    - Use get_category_fraud_history to understand category risk
    - Clearly explain the risk level and reasons
    - Always provide a recommended action: approve / manual_review / block
    - Be precise with numbers from the database""",
    tools=[check_transaction_risk, get_category_fraud_history]
)


# ── Test Runner ────────────────────────────────────

async def test_agent():
    """Test the fraud agent with real scenarios."""

    session_service = InMemorySessionService()
    runner = Runner(
        agent=fraud_agent,
        app_name="smartshop_fraud",
        session_service=session_service
    )

    session = await session_service.create_session(
        app_name="smartshop_fraud",
        user_id="test_user"
    )

    test_questions = [
        "Check if a $850 grocery transaction in CA is fraudulent",
        "Is a $15 electronics purchase in NY safe to approve?",
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
    print("  SmartShop Fraud Detection Agent")
    print("=" * 50)

    # Test 1: High risk transaction
    print("\n[TEST 1] High risk — $850 grocery in CA")
    try:
        result = check_transaction_risk(
            amount=850.00,
            category="grocery",
            state="CA"
        )
        print(f"  Risk level   : {result.get('risk_level')}")
        print(f"  Risk score   : {result.get('risk_score')}")
        print(f"  Action       : {result.get('recommended_action')}")
        print(f"  Fraud rate   : {result.get('category_fraud_rate')}%")
        print(f"  Reasons      : {result.get('reasons')}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 2: Low risk transaction
    print("\n[TEST 2] Low risk — $15 electronics in NY")
    try:
        result = check_transaction_risk(
            amount=15.00,
            category="electronics",
            state="NY"
        )
        print(f"  Risk level   : {result.get('risk_level')}")
        print(f"  Risk score   : {result.get('risk_score')}")
        print(f"  Action       : {result.get('recommended_action')}")
        print(f"  Fraud rate   : {result.get('category_fraud_rate')}%")
        print(f"  Reasons      : {result.get('reasons')}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 3: Fraud history for grocery category
    print("\n[TEST 3] Fraud history — grocery category")
    try:
        history = get_category_fraud_history("grocery")
        print(f"  Total txns   : {history.get('total_transactions', 0)}")
        print(f"  Fraud count  : {history.get('fraud_count', 0)}")
        print(f"  Fraud rate   : {history.get('fraud_rate_pct', 0)}%")
        print(f"  Avg amount   : ${float(history.get('avg_amount', 0)):.2f}")
        print(f"  Avg fraud amt: ${float(history.get('avg_fraud_amount', 0)):.2f}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 4: Fraud history for shopping category
    print("\n[TEST 4] Fraud history — shopping category")
    try:
        history = get_category_fraud_history("shopping")
        print(f"  Total txns   : {history.get('total_transactions', 0)}")
        print(f"  Fraud rate   : {history.get('fraud_rate_pct', 0)}%")
        print(f"  Avg amount   : ${float(history.get('avg_amount', 0)):.2f}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 5: Edge case — very high amount
    print("\n[TEST 5] Edge case — $5000 jewelry in TX")
    try:
        result = check_transaction_risk(
            amount=5000.00,
            category="misc_net",
            state="TX"
        )
        print(f"  Risk level   : {result.get('risk_level')}")
        print(f"  Risk score   : {result.get('risk_score')}")
        print(f"  Action       : {result.get('recommended_action')}")
        print(f"  Reasons      : {result.get('reasons')}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 6: Run agent with Gemini
    print("\n[TEST 6] Running agent with Gemini...")
    asyncio.run(test_agent())

    print("\n" + "=" * 50)
    print("  Fraud agent ready!")
    print("=" * 50)