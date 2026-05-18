import os
from dotenv import load_dotenv
from google.cloud import bigquery
import pandas as pd
from pathlib import Path

load_dotenv()

CLEAN_DATA_DIR = Path("data/clean")
PROJECT_ID     = os.getenv("PROJECT_ID", "smart-shop-ai-496616")
DATASET_ID     = os.getenv("BQ_DATASET", "smartshop")
BQ_LOCATION    = os.getenv("BQ_LOCATION", "US")

if not PROJECT_ID:
    raise RuntimeError(
        "PROJECT_ID is not set. Add PROJECT_ID to your .env file."
    )

print(f"Project  : {PROJECT_ID}")
print(f"Dataset  : {DATASET_ID}")
print(f"Location : {BQ_LOCATION}")

# Clean up invalid credential path if present
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
if credentials_path and (
    credentials_path == "/path/to/your-service-account.json"
    or not Path(credentials_path).exists()
):
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

try:
    client = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
    print(f"Connected to: {client.project} (location: {BQ_LOCATION})")
except Exception as e:
    raise RuntimeError(
        f"BigQuery connection failed.\n"
        f"Run: gcloud auth application-default login\n"
        f"Then: gcloud auth application-default set-quota-project {PROJECT_ID}\n"
        f"Error: {e}"
    ) from e


def create_dataset():
    dataset_ref      = f"{PROJECT_ID}.{DATASET_ID}"
    dataset          = bigquery.Dataset(dataset_ref)
    dataset.location = BQ_LOCATION    # ← uses env variable, not hardcoded
    try:
        client.create_dataset(dataset)
        print(f"Dataset '{DATASET_ID}' created in {BQ_LOCATION}!")
    except Exception:
        print(f"Dataset '{DATASET_ID}' already exists — skipping.")


def upload_table(df: pd.DataFrame, table_name: str):
    table_ref  = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True
    )
    job = client.load_table_from_dataframe(
        df, table_ref, job_config=job_config
    )
    job.result()
    table = client.get_table(table_ref)
    print(f"Uploaded {table.num_rows} rows → {table_ref}")


def upload_all():
    create_dataset()

    print("\nUploading products...")
    products = pd.read_csv(CLEAN_DATA_DIR / "products.csv")
    upload_table(products, "products")

    print("Uploading orders...")
    orders = pd.read_csv(CLEAN_DATA_DIR / "orders.csv")
    upload_table(orders, "orders")

    print("Uploading fraud transactions...")
    fraud = pd.read_csv(CLEAN_DATA_DIR / "fraud_transactions.csv")
    upload_table(fraud, "fraud_transactions")

    print("\nAll tables uploaded to BigQuery successfully!")


if __name__ == "__main__":
    upload_all()