import os
from dotenv import load_dotenv
from google.cloud import bigquery
import pandas as pd

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID") or os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("BQ_DATASET", "smartshop")

if not PROJECT_ID:
    raise RuntimeError(
        "PROJECT_ID is not set. Add PROJECT_ID to your .env file."
    )

# Handle invalid GOOGLE_APPLICATION_CREDENTIALS placeholder
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_path:
    credentials_path = os.path.expanduser(credentials_path)
    if credentials_path == "/path/to/your-service-account.json" or not os.path.exists(credentials_path):
        if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

try:
    client = bigquery.Client(project=PROJECT_ID)
except Exception as e:
    raise RuntimeError(
        f"BigQuery client initialization failed for project {PROJECT_ID}.\n"
        "Ensure gcloud ADC is configured: gcloud auth application-default login\n"
        f"Error: {e}"
    ) from e

def query_bigquery(sql: str) -> pd.DataFrame:
    """Run any SQL query on BigQuery and return a dataframe."""
    return client.query(sql).to_dataframe()

# ── Product Queries ────────────────────────────────

def get_products_by_category(category: str, max_price: float = None) -> list:
    """Fetch products from BigQuery by category and optional price filter."""
    price_filter = f"AND price <= {max_price}" if max_price else ""
    sql = f"""
        SELECT name, category, price, description
        FROM `{PROJECT_ID}.{DATASET_ID}.products`
        WHERE LOWER(category) LIKE LOWER('%{category}%')
        {price_filter}
        ORDER BY price ASC
        LIMIT 10
    """
    df = query_bigquery(sql)
    return df.to_dict(orient="records")

def search_products(keyword: str) -> list:
    """Full text search on product descriptions."""
    sql = f"""
        SELECT name, category, price, description
        FROM `{PROJECT_ID}.{DATASET_ID}.products`
        WHERE LOWER(description) LIKE LOWER('%{keyword}%')
        LIMIT 10
    """
    df = query_bigquery(sql)
    return df.to_dict(orient="records")

def get_product_stats() -> dict:
    """Get aggregate product statistics."""
    sql = f"""
        SELECT
            COUNT(*) as total_products,
            AVG(price) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price,
            COUNT(DISTINCT category) as total_categories
        FROM `{PROJECT_ID}.{DATASET_ID}.products`
    """
    df = query_bigquery(sql)
    return df.iloc[0].to_dict()

# ── Order Queries ──────────────────────────────────

def get_order_by_id(order_id: str) -> dict:
    """Fetch a specific order from BigQuery."""
    sql = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_ID}.orders`
        WHERE order_id = '{order_id}'
        LIMIT 1
    """
    df = query_bigquery(sql)
    if df.empty:
        return {"error": f"Order {order_id} not found"}
    return df.iloc[0].to_dict()

def get_customer_orders(customer_id: str) -> list:
    """Get all orders for a customer."""
    sql = f"""
        SELECT order_id, order_status, order_purchase_timestamp,
               total_amount, review_score
        FROM `{PROJECT_ID}.{DATASET_ID}.orders`
        WHERE customer_id = '{customer_id}'
        ORDER BY order_purchase_timestamp DESC
        LIMIT 5
    """
    df = query_bigquery(sql)
    return df.to_dict(orient="records")

# ── Fraud Queries ──────────────────────────────────

def get_fraud_patterns(category: str) -> dict:
    """Get historical fraud patterns for a merchant category."""
    sql = f"""
        SELECT
            category,
            COUNT(*) as total_transactions,
            SUM(fraud_label) as fraud_count,
            ROUND(AVG(fraud_label) * 100, 2) as fraud_rate_pct,
            AVG(amount) as avg_amount,
            AVG(CASE WHEN fraud_label = 1 THEN amount END) as avg_fraud_amount
        FROM `{PROJECT_ID}.{DATASET_ID}.fraud_transactions`
        WHERE LOWER(category) LIKE LOWER('%{category}%')
        GROUP BY category
    """
    df = query_bigquery(sql)
    if df.empty:
        return {"fraud_rate_pct": 0, "avg_fraud_amount": 0}
    return df.iloc[0].to_dict()

def analyze_transaction_risk(amount: float, category: str, state: str) -> dict:
    """Compare a transaction against historical fraud patterns."""
    sql = f"""
        SELECT
            ROUND(AVG(fraud_label) * 100, 2) as category_fraud_rate,
            AVG(amount) as avg_amount,
            STDDEV(amount) as stddev_amount
        FROM `{PROJECT_ID}.{DATASET_ID}.fraud_transactions`
        WHERE LOWER(category) LIKE LOWER('%{category}%')
          AND state = '{state}'
    """
    df = query_bigquery(sql)
    if df.empty:
        return {"risk": "UNKNOWN", "reason": "No historical data"}

    stats = df.iloc[0]
    avg   = stats["avg_amount"]
    std   = stats["stddev_amount"] or 1
    fraud_rate = stats["category_fraud_rate"]

    # Z-score: how far is this amount from average?
    z_score = abs(amount - avg) / std

    risk_score = 0
    reasons    = []

    if fraud_rate > 5:
        risk_score += 30
        reasons.append(f"High-risk category ({fraud_rate}% fraud rate)")
    if z_score > 2:
        risk_score += 40
        reasons.append(f"Unusual amount (${amount:.2f} vs avg ${avg:.2f})")
    if amount > 500:
        risk_score += 20
        reasons.append("High transaction amount")

    risk_level = (
        "LOW"    if risk_score < 30 else
        "MEDIUM" if risk_score < 60 else
        "HIGH"
    )

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "reasons": reasons,
        "category_fraud_rate": fraud_rate,
        "recommended_action": (
            "approve" if risk_level == "LOW" else
            "manual_review" if risk_level == "MEDIUM" else
            "block"
        )
    }