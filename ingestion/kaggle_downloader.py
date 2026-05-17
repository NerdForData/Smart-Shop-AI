import os
from pathlib import Path
from dotenv import load_dotenv
from kaggle.api.kaggle_api_extended import KaggleApi

# Load environment variables from .env
load_dotenv()

# Get Kaggle credentials from .env
KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME")
KAGGLE_KEY = os.getenv("KAGGLE_KEY")

# Set environment variables for Kaggle API
os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
os.environ["KAGGLE_KEY"] = KAGGLE_KEY

# Create datasets directory if it doesn't exist
DATASETS_DIR = Path(__file__).parent.parent / "datasets"
DATASETS_DIR.mkdir(exist_ok=True)

# Initialize Kaggle API
api = KaggleApi()
api.authenticate()

def download_dataset(dataset_id: str, name: str = None) -> None:
    """Download a Kaggle dataset to the datasets folder."""
    try:
        print(f"📥 Downloading {name or dataset_id}...")
        api.dataset_download_files(dataset_id, path=DATASETS_DIR, unzip=False)
        print(f"✓ {name or dataset_id} downloaded to {DATASETS_DIR}")
    except Exception as e:
        print(f"✗ Error downloading {name or dataset_id}: {e}")
        raise

if __name__ == "__main__":
    # Download datasets
    download_dataset("olistbr/brazilian-ecommerce", "Brazilian Ecommerce Dataset")
    download_dataset("kartik2112/fraud-detection", "Fraud Detection Dataset")
    print("\n✓ All datasets downloaded successfully!")
