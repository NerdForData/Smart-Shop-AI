import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# Allow loading the ADC credential path from .env if provided
google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if google_creds:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_creds

CLEAN_DATA_DIR = Path("data/clean")
# Read project and dataset from environment for safety
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
if not PROJECT_ID or PROJECT_ID == "your-gcp-project-id":
    raise RuntimeError(
        "GCP_PROJECT_ID is not set. Add GCP_PROJECT_ID=project-... to your .env or environment."
    )
DATASET_ID = os.getenv("BQ_DATASET", "smartshop")

try:
    from google.cloud import bigquery
except Exception as e:
    raise ImportError(
        "google-cloud-bigquery is not installed. Run 'pip install google-cloud-bigquery' in your environment"
    ) from e

try:
    client = bigquery.Client(project=PROJECT_ID)
except Exception as e:
    raise RuntimeError(
        "Unable to initialize BigQuery client. Ensure GOOGLE_APPLICATION_CREDENTIALS is set to a valid service account JSON file or run 'gcloud auth application-default login'."
    ) from e

def create_dataset():
    """Create BigQuery dataset if it doesn't exist."""
    if not client:
        raise RuntimeError(
            "BigQuery client not initialized. Ensure you have application default credentials set (set GOOGLE_APPLICATION_CREDENTIALS or run 'gcloud auth application-default login')"
        )

    dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "EU"

    try:
        client.create_dataset(dataset)
        print(f"Dataset {DATASET_ID} created!")
    except Exception:
        print(f"Dataset {DATASET_ID} already exists.")

def upload_table(df: pd.DataFrame, table_name: str):
    """Upload a dataframe to BigQuery."""
    if not client:
        raise RuntimeError(
            "BigQuery client not initialized. Ensure you have application default credentials set (set GOOGLE_APPLICATION_CREDENTIALS or run 'gcloud auth application-default login')"
        )
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",   # Replace table each time
        autodetect=True                        # Auto-detect schema
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()   # Wait for job to complete

    table = client.get_table(table_ref)
    print(f"Uploaded {table.num_rows} rows to {table_ref}")

def upload_all():
    create_dataset()

    # Upload products
    products = pd.read_csv(CLEAN_DATA_DIR / "products.csv")
    upload_table(products, "products")

    # Upload orders
    orders = pd.read_csv(CLEAN_DATA_DIR / "orders.csv")
    upload_table(orders, "orders")

    # Upload fraud data
    fraud = pd.read_csv(CLEAN_DATA_DIR / "fraud_transactions.csv")
    upload_table(fraud, "fraud_transactions")

    print("All tables uploaded to BigQuery!")

if __name__ == "__main__":
    upload_all()