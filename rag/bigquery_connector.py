# rag/bigquery_connector.py

import os
from dotenv import load_dotenv
from google.cloud import bigquery
import pandas as pd

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID", "project-368ffaff-af84-4aac-9b2")
DATASET_ID = os.getenv("BQ_DATASET", "smartshop")
BQ_LOCATION = os.getenv("BQ_LOCATION", "EU")

print(f"DEBUG - PROJECT_ID: {PROJECT_ID}")
print(f"DEBUG - DATASET_ID: {DATASET_ID}")
print(f"DEBUG - LOCATION:   {BQ_LOCATION}")

# Clean up bad credential path if still in .env
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
if credentials_path and (
    credentials_path == "/path/to/your-service-account.json"
    or not os.path.exists(credentials_path)
):
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

try:
    client = bigquery.Client(
        project=PROJECT_ID,
        location=BQ_LOCATION
    )
    print(f"BigQuery connected to: {client.project} (location: {BQ_LOCATION})")
except Exception as e:
    raise RuntimeError(f"BigQuery connection failed: {e}") from e


def query_bigquery(sql: str) -> pd.DataFrame:
    """Run SQL query on BigQuery with correct EU location."""
    job = client.query(sql, location=BQ_LOCATION)   # ← location on every query
    return job.to_dataframe()


# ── Product Queries ────────────────────────────────

def get_products_by_category(category: str, max_price: float = None) -> list:
    price_filter = f"AND price <= {max_price}" if max_price else ""
    sql = f"""
        SELECT name, category, price, description
        FROM `{PROJECT_ID}.{DATASET_ID}.products`
        WHERE LOWER(category) LIKE LOWER('%{category}%')
        {price_filter}
        ORDER BY price ASC
        LIMIT 10
    """
    return query_bigquery(sql).to_dict(orient="records")


def search_products(keyword: str) -> list:
    sql = f"""
        SELECT name, category, price, description
        FROM `{PROJECT_ID}.{DATASET_ID}.products`
        WHERE LOWER(description) LIKE LOWER('%{keyword}%')
        LIMIT 10
    """
    return query_bigquery(sql).to_dict(orient="records")


def get_product_stats() -> dict:
    sql = f"""
        SELECT
            COUNT(*)                 AS total_products,
            AVG(price)               AS avg_price,
            MIN(price)               AS min_price,
            MAX(price)               AS max_price,
            COUNT(DISTINCT category) AS total_categories
        FROM `{PROJECT_ID}.{DATASET_ID}.products`
    """
    return query_bigquery(sql).iloc[0].to_dict()


# ── Order Queries ──────────────────────────────────

def get_order_by_id(order_id: str) -> dict:
    sql = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_ID}.orders`
        WHERE order_id = '{order_id}'
        LIMIT 1
    """
    df = query_bigquery(sql)
    return df.iloc[0].to_dict() if not df.empty else {"error": f"Order {order_id} not found"}


def get_customer_orders(customer_id: str) -> list:
    sql = f"""
        SELECT order_id, order_status, order_purchase_timestamp,
               total_amount, review_score
        FROM `{PROJECT_ID}.{DATASET_ID}.orders`
        WHERE customer_id = '{customer_id}'
        ORDER BY order_purchase_timestamp DESC
        LIMIT 5
    """
    return query_bigquery(sql).to_dict(orient="records")


# ── Fraud Queries ──────────────────────────────────

def get_fraud_patterns(category: str) -> dict:
    sql = f"""
        SELECT
            category,
            COUNT(*)                          AS total_transactions,
            SUM(fraud_label)                  AS fraud_count,
            ROUND(AVG(fraud_label) * 100, 2)  AS fraud_rate_pct,
            AVG(amount)                       AS avg_amount,
            AVG(CASE WHEN fraud_label = 1
                THEN amount END)              AS avg_fraud_amount
        FROM `{PROJECT_ID}.{DATASET_ID}.fraud_transactions`
        WHERE LOWER(category) LIKE LOWER('%{category}%')
        GROUP BY category
    """
    df = query_bigquery(sql)
    return df.iloc[0].to_dict() if not df.empty \
        else {"fraud_rate_pct": 0, "avg_fraud_amount": 0}


def analyze_transaction_risk(amount: float, category: str, state: str) -> dict:
    sql = f"""
        SELECT
            ROUND(AVG(fraud_label) * 100, 2) AS category_fraud_rate,
            AVG(amount)                       AS avg_amount,
            STDDEV(amount)                    AS stddev_amount
        FROM `{PROJECT_ID}.{DATASET_ID}.fraud_transactions`
        WHERE LOWER(category) LIKE LOWER('%{category}%')
          AND state = '{state}'
    """
    df = query_bigquery(sql)
    if df.empty:
        return {"risk": "UNKNOWN", "reason": "No historical data"}

    stats      = df.iloc[0]
    avg        = stats["avg_amount"]
    std        = stats["stddev_amount"] or 1
    fraud_rate = stats["category_fraud_rate"]
    z_score    = abs(amount - avg) / std

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
        "risk_level":          risk_level,
        "risk_score":          risk_score,
        "reasons":             reasons,
        "category_fraud_rate": fraud_rate,
        "recommended_action": (
            "approve"       if risk_level == "LOW"    else
            "manual_review" if risk_level == "MEDIUM" else
            "block"
        )
    }


# ── Tests ──────────────────────────────────────────

if __name__ == "__main__":

    print("\n" + "=" * 50)
    print("  Testing BigQuery Connector")
    print("=" * 50)

    # Test 1: Product keyword search
    print("\n[TEST 1] Search products: keyword = 'watch'")
    try:
        results = search_products("watch")
        if results:
            for r in results[:3]:
                print(f"  → {r['name']} | {r['category']} | ${r['price']:.2f}")
        else:
            print("  ⚠ No results found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 2: Category + price filter
    print("\n[TEST 2] Electronics under $100")
    try:
        results = get_products_by_category("electronics", max_price=100)
        if results:
            for r in results[:3]:
                print(f"  → {r['name']} | ${r['price']:.2f}")
        else:
            print("  ⚠ No results found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 3: Catalog stats
    print("\n[TEST 3] Product catalog statistics")
    try:
        stats = get_product_stats()
        print(f"  Total products   : {int(stats['total_products'])}")
        print(f"  Avg price        : ${stats['avg_price']:.2f}")
        print(f"  Min price        : ${stats['min_price']:.2f}")
        print(f"  Max price        : ${stats['max_price']:.2f}")
        print(f"  Total categories : {int(stats['total_categories'])}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 4: Real order lookup
    print("\n[TEST 4] Fetch a real order from BigQuery")
    try:
        sample_df = query_bigquery(
            f"SELECT order_id FROM `{PROJECT_ID}.{DATASET_ID}.orders` LIMIT 1"
        )
        if not sample_df.empty:
            oid   = sample_df.iloc[0]["order_id"]
            order = get_order_by_id(oid)
            print(f"  Order ID     : {order.get('order_id')}")
            print(f"  Status       : {order.get('order_status')}")
            print(f"  Total Amount : ${float(order.get('total_amount', 0)):.2f}")
        else:
            print("  ⚠ No orders found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 5: Fraud patterns
    print("\n[TEST 5] Fraud patterns — category: 'grocery'")
    try:
        fraud = get_fraud_patterns("grocery")
        print(f"  Fraud rate   : {fraud.get('fraud_rate_pct', 0)}%")
        print(f"  Total txns   : {fraud.get('total_transactions', 0)}")
        print(f"  Avg amount   : ${float(fraud.get('avg_amount', 0)):.2f}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 6: Risk scoring
    print("\n[TEST 6] Risk score — $850 grocery transaction in CA")
    try:
        risk = analyze_transaction_risk(850.00, "grocery", "CA")
        print(f"  Risk level   : {risk.get('risk_level')}")
        print(f"  Risk score   : {risk.get('risk_score')}")
        print(f"  Action       : {risk.get('recommended_action')}")
        print(f"  Reasons      : {risk.get('reasons')}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    print("\n" + "=" * 50)
    print("  All tests completed!")
    print("=" * 50 + "\n")