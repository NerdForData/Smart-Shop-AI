# Smart-Shop-AI

An intelligent multi-agent e-commerce AI system powered by real Brazilian e-commerce and fraud detection data from BigQuery. The system intelligently routes user queries to specialized agents (Support, Recommender, and Fraud Detection) that work with actual historical data to provide informed responses.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Getting Started](#getting-started)
- [Running the Project](#running-the-project)
- [API Usage](#api-usage)
- [Development](#development)
- [Deployment](#deployment)

---

## 🎯 Project Overview

**Why This Project?**
- **Real-world E-commerce Intelligence**: Most AI chat systems use generic knowledge; this system leverages actual Brazilian e-commerce transaction data (50k+ transactions) and fraud patterns to provide contextual insights
- **Multi-Agent Architecture**: Rather than a single monolithic AI model, specialized agents handle different domains (customer support, product recommendations, fraud detection) more effectively
- **Production-Ready**: Integrated with Google Cloud infrastructure (BigQuery, Gemini API), containerized deployment, and built-in safety guardrails

**Key Features**
- 🤖 **Support Agent**: Answers customer inquiries, looks up orders, searches products with real data
- 📊 **Recommender Agent**: Provides semantic product recommendations based on embeddings from real product catalog
- 🛡️ **Fraud Agent**: Analyzes transaction risk patterns against historical fraud data
- 🔒 **Safety Guardrails**: Rule-based content filtering to prevent harmful requests
- 🗄️ **BigQuery Integration**: All agent tools query live BigQuery tables with real data
- 📝 **Vector Search**: Semantic search on product descriptions using Chroma embeddings

---

## 🏗️ Architecture

```
User Request (Chat API)
         ↓
   [FastAPI Endpoint]
         ↓
   [Intent Router - LangGraph]
         ↓
    ┌────┴────┬──────────────┐
    ↓         ↓              ↓
[Support] [Recommender]  [Fraud Detection]
    ↓         ↓              ↓
[BigQuery Tools] [Vector Store + BQ] [Fraud Pattern Analysis]
    ↓         ↓              ↓
    └────┬────┴──────────────┘
         ↓
   [Guardrails Check]
         ↓
   Chat Response
```

**Why LangGraph?** Manages complex agent workflows with state, allows tool calling, and integrates multiple LLMs. Replaces custom routing logic with a proven framework.

**Why BigQuery?** Enables:
- Scalable querying of 50k+ transactions
- Real-time analysis of fraud patterns
- Managed infrastructure for compliance and backups
- Direct SQL queries without moving data

**Why Vector Store (Chroma)?** For semantic product search rather than keyword matching, enabling natural language queries like "waterproof laptop bags" to find relevant products.

---

## 📂 Directory Structure

### `/api/` - FastAPI Application
**Files**: `main.py`

**Purpose**: Exposes REST endpoints for the chat interface

**Key Components**:
- `POST /chat` - Main endpoint accepting user messages and routing to agents
- `GET /health` - Health check endpoint
- CORS middleware for cross-origin requests
- Request/response validation using Pydantic

**Why FastAPI?** Async support, automatic API documentation, fast performance, and built-in validation. Python ecosystem aligns with agent development.

---

### `/agents/` - Specialized AI Agents
**Files**: `support_agent.py`, `recommender_agent.py`, `fraud_agent.py`

**Purpose**: Each agent handles a specific domain with custom tools

**Support Agent** (`support_agent.py`)
- **Tools**: `lookup_order()`, `get_my_orders()`, `search_for_product()`
- **Why**: Handles customer service queries. Direct BigQuery queries provide accurate, real-time order and product information instead of generic responses
- **Example**: "Where is my order?" → queries actual order database

**Recommender Agent** (`recommender_agent.py`)
- **Tools**: `semantic_product_search()`, `get_category_products()`, `get_product_stats()`
- **Why**: Uses vector embeddings for semantic understanding. Customers describe products naturally (e.g., "comfortable laptop bags"), not exact product names
- **Vector Store**: Pre-loaded Chroma database with product embeddings
- **Example**: "I need a gift for my mom" → semantic search finds relevant products

**Fraud Agent** (`fraud_agent.py`)
- **Tools**: `check_transaction_risk()`, `get_category_fraud_history()`
- **Why**: Detects suspicious patterns against historical data. Protects platform by analyzing transaction amounts, categories, and geographic anomalies
- **Data-Driven**: Patterns derived from 5000+ historical fraud cases
- **Example**: "Is this transaction risky?" → analyzed against fraud patterns

**Why Google ADK (Agent Development Kit)?** Provides structured agent framework with built-in tool management, session handling, and integration with Gemini models.

---

### `/orchestrator/` - Agent Routing & State Management
**Files**: `graph.py`

**Purpose**: Determines which agent should handle each user query

**Key Responsibilities**:
1. **Intent Recognition**: Determines if query is about support, recommendations, or fraud
2. **State Management**: Maintains conversation context using TypedDict
3. **Agent Selection**: Routes to appropriate agent based on intent
4. **Response Synthesis**: Combines agent outputs into final response

**Why LangGraph?** 
- Replaces complex if-else routing with a proper state machine
- Enables future enhancements like multi-agent collaboration
- Handles tool calling and result processing automatically

---

### `/rag/` - Data Access & Retrieval
**Files**: `bigquery_connector.py`, `vector_store.py`

**Purpose**: Abstracts all data access, providing single source of truth

**bigquery_connector.py**
- Manages BigQuery client and authentication
- Provides functions: `query_bigquery()`, `get_products_by_category()`, `analyze_transaction_risk()`, etc.
- **Why**: Centralizes connection logic, handles credentials, makes BigQuery queries feel like function calls
- Queries real tables: `products`, `orders`, `customers`, `fraud_patterns`

**vector_store.py**
- Manages Chroma vector database for product embeddings
- Pre-loads embeddings at startup (not runtime) for performance
- **Why**: Semantic search requires vector representation; Chroma is lightweight and in-process

**Why Separate RAG Layer?** Decouples agents from implementation details. Could swap BigQuery with PostgreSQL without changing agent code.

---

### `/guardrails/` - Safety & Content Filtering
**Files**: `guardrails_manager.py`, `config.yml`

**Purpose**: Prevents misuse before responses are generated

**Implementation**:
- Rule-based pattern matching for harmful intent
- Patterns include: "hack", "steal", "scam", "commit fraud", etc.
- Applied to user messages before routing to agents

**Why Rule-Based Instead of LLM?** 
- Faster (no API calls)
- Deterministic (no hallucinations)
- Cost-effective (already checking with Gemini for routing)
- Explicitly auditable

---

### `/ingestion/` - Data Pipeline
**Files**: `kaggle_downloader.py`, `data_cleaner.py`, `bigquery_uploader.py`

**Purpose**: Manages data from source to BigQuery

**Workflow**:
1. **kaggle_downloader.py**: Downloads datasets from Kaggle → `datasets/` and `data/raw/`
2. **data_cleaner.py**: Cleans, deduplicates, transforms → `data/clean/`
3. **bigquery_uploader.py**: Uploads cleaned data → BigQuery tables

**Why Separate Ingestion?**
- Decouples data preparation from model serving
- Allows scheduling pipeline runs independently
- Enables data versioning and auditing

---

### `/data/` - Local Data Storage
**Structure**:
- `raw/` - Original Kaggle datasets (before cleaning)
- `clean/` - Processed data ready for BigQuery upload

**Note**: Large files excluded from git. Regenerate with pipeline or download manually.

---

### `/datasets/` - Kaggle Dataset Mirror
**Purpose**: Intermediate storage after Kaggle download, before processing

---

### `/k8s/` - Kubernetes Deployment
**Files**: `deployment.yaml`, `service.yaml`, `configmap.yaml`, `secrets.yaml`, `autoscaler.yaml`, `storage.yaml`, `namespace.yaml`

**Why Kubernetes?**
- Auto-scaling based on request volume
- Self-healing (restarts failed pods)
- Rolling updates without downtime
- Secrets management for credentials
- Horizontal scaling across multiple replicas

**Key Configuration**:
- Namespace: `smart-shop-ai`
- Service: Exposes FastAPI on port 8000
- ConfigMap: Stores non-secret config (project ID, dataset name)
- Secrets: Stores API keys, credentials
- Deployment: 2 replicas, CPU/memory limits
- HPA: Scales 1-5 pods based on CPU usage

---

### `/terraform/` - Infrastructure as Code
**Files**: `main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars`

**Purpose**: Provisions GCP resources programmatically

**Resources Created**:
- GCP Project configuration
- BigQuery datasets and tables
- Kubernetes cluster setup
- Service accounts and IAM roles

**Why Terraform?** Version control infrastructure, reproducible deployments, easy teardown for cost management.

---

### Docker & Containerization
**Files**: `Dockerfile`, `docker-compose.yml`

**Why Containerization?**
- Consistent environment from dev → prod
- Easy local testing with `docker-compose`
- Portable across any infrastructure
- Dependency isolation

**Dockerfile**:
- Base: Python 3.11-slim (lightweight)
- Installs requirements
- Sets up working directory
- Runs FastAPI via Uvicorn

**docker-compose.yml**: Orchestrates multiple services locally (API, potentially database services)

---

### Configuration
**Files**: `.env`, `requirements.txt`

**.env (Template)**:
```env
# Google Cloud
GOOGLE_API_KEY=your_gemini_api_key
PROJECT_ID=smart-shop-ai-496616
BQ_DATASET=smartshop

# Kaggle (for downloading data)
KAGGLE_USERNAME=your_username
KAGGLE_KEY=your_key

# Optional
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

**requirements.txt**: All Python dependencies pinned to versions for reproducibility

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (optional, for containerized setup)
- Kaggle account with API token
- Google Cloud account with BigQuery

### 1. Clone & Setup

```bash
git clone <repository>
cd Smart-Shop-AI
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Download Datasets

Create `.env` file:
```bash
touch .env
```

Add credentials:
```text
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_key
```

Download and process:
```bash
python ingestion/kaggle_downloader.py  # Downloads from Kaggle
python ingestion/data_cleaner.py       # Cleans and transforms
```

### 3. Setup BigQuery

Get Google API key:
1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Create API key
3. Add to `.env`:

```text
GOOGLE_API_KEY=your_api_key
PROJECT_ID=smart-shop-ai-496616
BQ_DATASET=smartshop
```

Upload cleaned data:
```bash
python ingestion/bigquery_uploader.py
```

### 4. Load Vector Store (Optional but Recommended)

The recommender agent uses pre-computed embeddings for semantic search. Pre-load them:
```bash
python -c "from rag.vector_store import load_vector_store; load_vector_store()"
```

---

## ▶️ Running the Project

### Local Development

```bash
source .venv/bin/activate
python -m uvicorn api.main:app --reload --port 8000
```

Access at `http://localhost:8000`

### Docker

```bash
docker-compose up --build
```

### Testing the API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you recommend a laptop bag?",
    "user_id": "user123"
  }'
```

---

## 🔌 API Usage

### `/chat` (POST)

**Request**:
```json
{
  "message": "What orders do I have?",
  "user_id": "customer_42"
}
```

**Response**:
```json
{
  "response": "You have 3 orders...",
  "agent_used": "support_agent",
  "execution_time_ms": 245
}
```

**Supported Queries**:
- Support: "Where is my order?", "Search for running shoes", "What's the status of order ABC123?"
- Recommendations: "Recommend products for outdoor activities", "I need a gift"
- Fraud: "Is this transaction suspicious?", "Check if $500 laptop purchase is normal"

### `/health` (GET)

```bash
curl http://localhost:8000/health
```

---

## 🛠️ Development

### Project Structure Philosophy

1. **Separation of Concerns**: Agents don't know about HTTP; API doesn't know about data fetching
2. **Testability**: Each module (agents, RAG, guardrails) can be tested independently
3. **Scalability**: Easy to add new agents, data sources, or LLM providers

### Adding a New Agent

1. Create `agents/my_agent.py` with tool functions
2. Define agent using Google ADK
3. Add routing logic in `orchestrator/graph.py`
4. Add corresponding data functions in `rag/bigquery_connector.py`

### Adding a New Data Source

1. Add query function to `rag/bigquery_connector.py`
2. Call it from appropriate agent tool
3. No changes needed to API or orchestrator

---

## 📦 Deployment

### To Google Cloud Run

```bash
gcloud run deploy smart-shop-ai \
  --source . \
  --region us-central1 \
  --set-env-vars PROJECT_ID=smart-shop-ai-496616,BQ_DATASET=smartshop \
  --set-secrets GOOGLE_API_KEY=GOOGLE_API_KEY:latest
```

### To Kubernetes Cluster

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/autoscaler.yaml
```

---

## 📊 Data Dictionary

### BigQuery Tables (After Ingestion)

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `products` | Product catalog | id, name, category, price, description |
| `orders` | Customer orders | id, customer_id, total, created_at |
| `customers` | Customer data | id, state, city |
| `fraud_patterns` | Historical fraud analysis | amount_range, category, fraud_rate |

---

## 🔐 Security Notes

- API keys stored in `.env` (not committed to git)
- BigQuery access controlled via IAM
- Guardrails filter harmful requests
- Kubernetes secrets for production credentials
- No customer PII logged in responses

---

## 📝 Common Issues & Solutions

**"GOOGLE_API_KEY not set"**
- Add to `.env` and restart API
- Verify key is valid at [AI Studio](https://aistudio.google.com/apikey)

**"BigQuery connection failed"**
- Check PROJECT_ID and BQ_DATASET in `.env`
- Verify authentication: `gcloud auth application-default login`
- Ensure tables exist: `bq ls --project_id=smart-shop-ai-496616 smartshop`

**"Vector store not found"**
- Pre-load embeddings: `python -c "from rag.vector_store import load_vector_store; load_vector_store()"`

**"Docker build fails"**
- Clear cache: `docker-compose build --no-cache`
- Check Python version: need 3.11+

---

## 📚 Additional Resources

- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [Google ADK Guide](https://ai.google.dev/guide)
- [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices)
- [Chroma Vector Store](https://docs.trychroma.com/)

---

## 📄 Notes

- Large dataset files are intentionally excluded from git to keep repository size manageable
- Datasets are regenerated via the ingestion pipeline or downloaded fresh from Kaggle
- For team collaboration, share dataset via BigQuery views or export specific tables
- Vector embeddings are pre-computed and cached in Chroma for performance

---

**Last Updated**: May 2026
