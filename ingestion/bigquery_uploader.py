import os
from dotenv import load_dotenv
from google.cloud import bigquery
import pandas as pd
from pathlib import Path

load_dotenv()

CLEAN_DATA_DIR = Path("data/clean")
PROJECT_ID = os.getenv("PROJECT_ID") or os.getenv("GCP_PROJECT_ID")
DATASET_ID = "smartshop"

if not PROJECT_ID:
    raise RuntimeError(
        "GCP project ID is not set. Add PROJECT_ID or GCP_PROJECT_ID to your .env file."
    )

# Handle GOOGLE_APPLICATION_CREDENTIALS from .env or shell
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_path:
    credentials_path = os.path.expanduser(credentials_path)
    # Remove placeholder or invalid paths so gcloud ADC can be used instead
    if credentials_path == "/path/to/your-service-account.json" or not Path(credentials_path).exists():
        del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        credentials_path = None
    else:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

try:
    from google.cloud import bigquery
except Exception as e:
    raise ImportError(
        "google-cloud-bigquery is not installed. Run 'pip install google-cloud-bigquery'"
    ) from e

# gcloud ADC handles auth if no explicit credentials file is given
try:
    client = bigquery.Client(project=PROJECT_ID)
    print(f"Connected to: {client.project}")
except Exception as e:
    raise RuntimeError(
        "BigQuery connection failed.\n"
        "Set GOOGLE_APPLICATION_CREDENTIALS to a valid service account JSON file, "
        "or authenticate with gcloud:\n"
        "  gcloud auth application-default login\n"
        f"Project: {PROJECT_ID}\n"
        f"Error: {e}"
    ) from e

def create_dataset():
    dataset_ref      = f"{PROJECT_ID}.{DATASET_ID}"
    dataset          = bigquery.Dataset(dataset_ref)
    dataset.location = "EU"
    try:
        client.create_dataset(dataset)
        print(f"Dataset '{DATASET_ID}' created!")
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