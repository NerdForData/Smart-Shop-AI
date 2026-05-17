import pandas as pd
from pathlib import Path

RAW_DATA_DIR  = Path("data/raw")
CLEAN_DATA_DIR = Path("data/clean")
CLEAN_DATA_DIR.mkdir(parents=True, exist_ok=True)

def clean_products():
    """Clean and prepare product data."""
    print("Cleaning product data...")

    # Load raw data
    products = pd.read_csv(RAW_DATA_DIR / "olist_products_dataset.csv")
    translations = pd.read_csv(RAW_DATA_DIR / "product_category_name_translation.csv")
    items = pd.read_csv(RAW_DATA_DIR / "olist_order_items_dataset.csv")

    # Merge to get prices
    products = products.merge(translations, on="product_category_name", how="left")
    products = products.merge(
        items[["product_id", "price"]].groupby("product_id").mean().reset_index(),
        on="product_id",
        how="left"
    )

    # Clean columns
    products = products[[
        "product_id",
        "product_category_name_english",
        "product_weight_g",
        "price"
    ]].rename(columns={
        "product_category_name_english": "category",
        "product_weight_g": "weight_grams"
    })

    # Remove nulls and duplicates
    products = products.dropna(subset=["category", "price"])
    products = products.drop_duplicates(subset="product_id")

    # Add readable product names (category + id suffix)
    products["name"] = (
        products["category"].str.replace("_", " ").str.title()
        + " #" + products["product_id"].str[:6]
    )

    # Add description for RAG
    products["description"] = (
        "Product: " + products["name"] +
        " | Category: " + products["category"] +
        " | Price: $" + products["price"].round(2).astype(str) +
        " | Weight: " + products["weight_grams"].astype(str) + "g"
    )

    products.to_csv(CLEAN_DATA_DIR / "products.csv", index=False)
    print(f"Products cleaned: {len(products)} rows")
    return products

def clean_orders():
    """Clean and prepare orders data."""
    print("Cleaning orders data...")

    orders   = pd.read_csv(RAW_DATA_DIR / "olist_orders_dataset.csv")
    reviews  = pd.read_csv(RAW_DATA_DIR / "olist_order_reviews_dataset.csv")
    items    = pd.read_csv(RAW_DATA_DIR / "olist_order_items_dataset.csv")

    # Merge datasets
    orders = orders.merge(
        reviews[["order_id", "review_score"]],
        on="order_id", how="left"
    )
    orders = orders.merge(
        items.groupby("order_id")["price"].sum().reset_index().rename(
            columns={"price": "total_amount"}
        ),
        on="order_id", how="left"
    )

    # Keep relevant columns
    orders = orders[[
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "total_amount",
        "review_score"
    ]].dropna()

    orders.to_csv(CLEAN_DATA_DIR / "orders.csv", index=False)
    print(f"Orders cleaned: {len(orders)} rows")
    return orders

def clean_fraud_data():
    """Clean fraud detection data."""
    print("Cleaning fraud data...")

    fraud = pd.read_csv(RAW_DATA_DIR / "fraudTrain.csv")

    # Keep relevant columns
    fraud = fraud[[
        "trans_num",
        "amt",
        "merchant",
        "category",
        "city",
        "state",
        "is_fraud"
    ]].rename(columns={
        "trans_num": "transaction_id",
        "amt": "amount",
        "is_fraud": "fraud_label"
    })

    fraud = fraud.dropna().drop_duplicates(subset="transaction_id")

    fraud.to_csv(CLEAN_DATA_DIR / "fraud_transactions.csv", index=False)
    print(f"Fraud data cleaned: {len(fraud)} rows")
    return fraud

if __name__ == "__main__":
    clean_products()
    clean_orders()
    clean_fraud_data()
    print("All data cleaned successfully!")