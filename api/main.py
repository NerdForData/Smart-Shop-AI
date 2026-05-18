# api/main.py

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix module path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Set API key before importing anything
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time

from orchestrator.graph import orchestrator
from guardrails.guardrails_manager import apply_guardrails


# ── App Setup ──────────────────────────────────────

app = FastAPI(
    title="SmartShop AI",
    description="Multi-agent e-commerce AI powered by real BigQuery data",
    version="1.0.0"
)

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# ── Request / Response Models ──────────────────────

class ChatRequest(BaseModel):
    message:  str
    user_id:  Optional[str] = "anonymous"

class ChatResponse(BaseModel):
    response:     str
    intent:       str
    blocked:      bool
    block_reason: Optional[str] = None
    latency_ms:   float
    user_id:      str

class HealthResponse(BaseModel):
    status:  str
    version: str
    agents:  list


# ── Routes ────────────────────────────────────────

@app.get("/", tags=["General"])
def root():
    return {
        "name":    "SmartShop AI",
        "version": "1.0.0",
        "status":  "running",
        "docs":    "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
def health():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        agents=["support_agent", "recommender_agent", "fraud_agent"]
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest):
    """
    Main chat endpoint.
    1. Runs guardrails on input
    2. Routes to correct agent via LangGraph
    3. Runs guardrails on output
    4. Returns safe response
    """
    start_time = time.time()

    # Validate message
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    if len(request.message) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Message too long. Maximum 1000 characters."
        )

    # Step 1: Input guardrails
    input_check = apply_guardrails(request.message)
    if input_check["blocked"]:
        latency = (time.time() - start_time) * 1000
        return ChatResponse(
            response=input_check["response"],
            intent="BLOCKED",
            blocked=True,
            block_reason=input_check["reason"],
            latency_ms=round(latency, 2),
            user_id=request.user_id
        )

    # Step 2: Run through LangGraph orchestrator
    try:
        result = orchestrator.invoke({
            "user_message":   request.message,
            "intent":         "",
            "agent_response": "",
            "tool_results":   {},
            "error":          None
        })

        agent_response = result.get("agent_response", "")
        intent         = result.get("intent", "UNKNOWN")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Orchestrator error: {str(e)}"
        )

    # Step 3: Output guardrails
    output_check = apply_guardrails(request.message, agent_response)
    if output_check["blocked"]:
        latency = (time.time() - start_time) * 1000
        return ChatResponse(
            response=output_check["response"],
            intent=intent,
            blocked=True,
            block_reason=output_check["reason"],
            latency_ms=round(latency, 2),
            user_id=request.user_id
        )

    latency = (time.time() - start_time) * 1000

    return ChatResponse(
        response=agent_response,
        intent=intent,
        blocked=False,
        block_reason=None,
        latency_ms=round(latency, 2),
        user_id=request.user_id
    )


@app.get("/stats", tags=["General"])
def catalog_stats():
    """Get live product catalog statistics from BigQuery."""
    try:
        from rag.bigquery_connector import get_product_stats
        stats = get_product_stats()
        return {
            "total_products":   int(stats["total_products"]),
            "avg_price":        round(float(stats["avg_price"]), 2),
            "min_price":        round(float(stats["min_price"]), 2),
            "max_price":        round(float(stats["max_price"]), 2),
            "total_categories": int(stats["total_categories"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Run ────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )