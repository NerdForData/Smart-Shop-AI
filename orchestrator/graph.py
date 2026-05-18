# orchestrator/graph.py

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix module path
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

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from agents.support_agent import support_agent, lookup_order, get_my_orders, search_for_product
from agents.recommender_agent import recommender_agent, semantic_product_search, get_category_products, get_catalog_overview
from agents.fraud_agent import fraud_agent, check_transaction_risk, get_category_fraud_history


# ── State Definition ───────────────────────────────

class ShopState(TypedDict):
    user_message:   str
    intent:         str
    agent_response: str
    tool_results:   dict
    error:          Optional[str]


# ── Intent Classification ──────────────────────────

def classify_intent(state: ShopState) -> ShopState:
    """
    Classify user message into one of:
    SUPPORT, RECOMMEND, FRAUD_CHECK, UNKNOWN
    Uses keyword matching — no LLM call needed,
    so no quota is consumed.
    """
    message = state["user_message"].lower()

    # Fraud detection keywords
    fraud_keywords = [
        "fraud", "suspicious", "transaction", "payment",
        "charge", "risk", "block", "approve", "fraudulent"
    ]

    # Recommendation keywords
    recommend_keywords = [
        "recommend", "suggest", "looking for", "find me",
        "show me", "want to buy", "gift", "best", "cheap",
        "under $", "budget", "search"
    ]

    # Support keywords
    support_keywords = [
        "order", "delivery", "return", "refund", "status",
        "track", "cancel", "complaint", "help", "support",
        "where is", "my order", "customer"
    ]

    # Score each intent
    fraud_score    = sum(1 for k in fraud_keywords    if k in message)
    recommend_score = sum(1 for k in recommend_keywords if k in message)
    support_score  = sum(1 for k in support_keywords  if k in message)

    # Pick highest score
    scores = {
        "FRAUD_CHECK": fraud_score,
        "RECOMMEND":   recommend_score,
        "SUPPORT":     support_score
    }

    intent = max(scores, key=scores.get)

    # Default to RECOMMEND if no keywords matched
    if scores[intent] == 0:
        intent = "RECOMMEND"

    print(f"  [Orchestrator] Intent classified: {intent}")
    print(f"  [Orchestrator] Scores: {scores}")

    return {**state, "intent": intent}


# ── Agent Nodes ────────────────────────────────────

def support_node(state: ShopState) -> ShopState:
    """Route to support agent tools directly."""
    message = state["user_message"].lower()
    results = {}

    try:
        # Check for order lookup
        if any(w in message for w in ["order", "status", "track", "delivery"]):
            from rag.bigquery_connector import query_bigquery, PROJECT_ID, DATASET_ID
            sample = query_bigquery(
                f"SELECT order_id, customer_id "
                f"FROM `{PROJECT_ID}.{DATASET_ID}.orders` LIMIT 1"
            )
            if not sample.empty:
                order_id = sample.iloc[0]["order_id"]
                results["order"] = lookup_order(order_id)

        # Always search for relevant products
        keywords = [w for w in message.split()
                   if len(w) > 3 and w not in
                   ["what", "where", "when", "help", "with", "have", "your"]]
        if keywords:
            results["products"] = search_for_product(keywords[0])[:3]

        # Format response
        response_parts = []
        if "order" in results:
            order = results["order"]
            response_parts.append(
                f"Order {order.get('order_id', 'N/A')}: "
                f"Status = {order.get('order_status', 'N/A')}, "
                f"Amount = ${float(order.get('total_amount', 0)):.2f}"
            )
        if "products" in results and results["products"]:
            prods = results["products"]
            prod_list = ", ".join([f"{p['name']} (${p['price']:.2f})"
                                   for p in prods[:3]])
            response_parts.append(f"Related products: {prod_list}")

        response = " | ".join(response_parts) if response_parts \
            else "I can help with your order and product questions!"

    except Exception as e:
        response = f"Support error: {e}"
        results = {"error": str(e)}

    return {**state, "agent_response": response, "tool_results": results}


def recommend_node(state: ShopState) -> ShopState:
    """Route to recommender agent tools directly."""
    message = state["user_message"]
    results = {}

    try:
        # Semantic search on the full message
        search_results = semantic_product_search(message)
        results["semantic_search"] = search_results

        # Get catalog overview
        results["catalog_stats"] = get_catalog_overview()

        # Format response
        if search_results:
            prod_list = "\n".join([
                f"  - {p['name']} | {p['category']} | ${p['price']:.2f}"
                for p in search_results[:5]
            ])
            response = (
                f"Based on your request, here are my recommendations:\n"
                f"{prod_list}\n"
                f"(From a catalog of "
                f"{int(results['catalog_stats']['total_products'])} products)"
            )
        else:
            response = "No matching products found. Try a different search."

    except Exception as e:
        response = f"Recommendation error: {e}"
        results = {"error": str(e)}

    return {**state, "agent_response": response, "tool_results": results}


def fraud_node(state: ShopState) -> ShopState:
    """Route to fraud agent tools directly."""
    message = state["user_message"].lower()
    results = {}

    try:
        # Extract amount from message if present
        import re
        amount_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', message)
        amount = float(amount_match.group(1).replace(",", "")) \
            if amount_match else 100.0

        # Extract state code if present (2 capital letters)
        state_match = re.search(r'\b([A-Z]{2})\b', state["user_message"])
        state_code  = state_match.group(1) if state_match else "CA"

        # Extract category keywords
        category = "grocery"
        category_keywords = {
            "grocery":     ["grocery", "food", "supermarket"],
            "electronics": ["electronic", "tech", "device", "phone"],
            "shopping":    ["shop", "retail", "store", "buy"],
            "gas":         ["gas", "fuel", "station"],
            "entertainment": ["entertainment", "movie", "game"]
        }
        for cat, keywords in category_keywords.items():
            if any(k in message for k in keywords):
                category = cat
                break

        # Run fraud check
        risk_result = check_transaction_risk(amount, category, state_code)
        results["risk_analysis"] = risk_result

        # Get category fraud history
        history = get_category_fraud_history(category)
        results["category_history"] = history

        # Format response
        response = (
            f"Fraud Analysis Results:\n"
            f"  Amount    : ${amount:.2f}\n"
            f"  Category  : {category}\n"
            f"  State     : {state_code}\n"
            f"  Risk Level: {risk_result.get('risk_level', 'UNKNOWN')}\n"
            f"  Risk Score: {risk_result.get('risk_score', 0)}\n"
            f"  Action    : {risk_result.get('recommended_action', 'review')}\n"
            f"  Reasons   : {', '.join(risk_result.get('reasons', ['None']))}\n"
            f"  Category fraud rate: "
            f"{history.get('fraud_rate_pct', 0)}%"
        )

    except Exception as e:
        response = f"Fraud check error: {e}"
        results = {"error": str(e)}

    return {**state, "agent_response": response, "tool_results": results}


def unknown_node(state: ShopState) -> ShopState:
    """Handle unknown intents."""
    return {
        **state,
        "agent_response": (
            "I can help you with:\n"
            "- Product recommendations (e.g. 'find me running shoes')\n"
            "- Order support (e.g. 'where is my order')\n"
            "- Fraud checks (e.g. 'check if $500 transaction is safe')\n"
            "What would you like help with?"
        ),
        "tool_results": {}
    }


# ── Routing Logic ──────────────────────────────────

def route_to_agent(state: ShopState) -> str:
    """Route to correct agent based on classified intent."""
    intent = state.get("intent", "UNKNOWN")
    routes = {
        "SUPPORT":     "support",
        "RECOMMEND":   "recommend",
        "FRAUD_CHECK": "fraud",
        "UNKNOWN":     "unknown"
    }
    return routes.get(intent, "unknown")


# ── Build the Graph ────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(ShopState)

    # Add nodes
    graph.add_node("classify", classify_intent)
    graph.add_node("support",  support_node)
    graph.add_node("recommend", recommend_node)
    graph.add_node("fraud",    fraud_node)
    graph.add_node("unknown",  unknown_node)

    # Entry point
    graph.set_entry_point("classify")

    # Conditional routing after classification
    graph.add_conditional_edges(
        "classify",
        route_to_agent,
        {
            "support":  "support",
            "recommend": "recommend",
            "fraud":    "fraud",
            "unknown":  "unknown"
        }
    )

    # All agent nodes go to END
    graph.add_edge("support",  END)
    graph.add_edge("recommend", END)
    graph.add_edge("fraud",    END)
    graph.add_edge("unknown",  END)

    return graph.compile()


# ── Main Orchestrator ──────────────────────────────

orchestrator = build_graph()


# ── Tests ──────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 55)
    print("  SmartShop AI — LangGraph Orchestrator")
    print("=" * 55)

    test_cases = [
        {
            "message": "I'm looking for running shoes under $50",
            "expected_intent": "RECOMMEND"
        },
        {
            "message": "Where is my order? I need help with delivery",
            "expected_intent": "SUPPORT"
        },
        {
            "message": "Check if a $850 transaction in CA is fraudulent",
            "expected_intent": "FRAUD_CHECK"
        },
        {
            "message": "Show me cheap electronics",
            "expected_intent": "RECOMMEND"
        },
        {
            "message": "I want to return my order and get a refund",
            "expected_intent": "SUPPORT"
        },
        {
            "message": "Is a suspicious $2000 payment from TX safe?",
            "expected_intent": "FRAUD_CHECK"
        },
    ]

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'─' * 55}")
        print(f"[TEST {i}] {test['message']}")
        print(f"Expected intent: {test['expected_intent']}")

        try:
            result = orchestrator.invoke({
                "user_message":   test["message"],
                "intent":         "",
                "agent_response": "",
                "tool_results":   {},
                "error":          None
            })

            actual_intent = result.get("intent", "UNKNOWN")
            intent_match  = actual_intent == test["expected_intent"]

            if intent_match:
                passed += 1
                print(f"Intent    : ✅ {actual_intent}")
            else:
                failed += 1
                print(f"Intent    : ❌ Got {actual_intent}, "
                      f"expected {test['expected_intent']}")

            print(f"Response  :\n{result.get('agent_response', 'No response')}")

        except Exception as e:
            failed += 1
            print(f"  ✗ Error: {e}")

    print(f"\n{'=' * 55}")
    print(f"  Results: {passed}/{len(test_cases)} tests passed")
    print(f"{'=' * 55}\n")