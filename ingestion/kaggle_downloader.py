import os
import zipfile
import kaggle
from pathlib import Path

RAW_DATA_DIR = Path("data/raw")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

def download_ecommerce_data():
    """Download Brazilian E-Commerce dataset from Kaggle."""
    print("Downloading E-Commerce dataset...")
    kaggle.api.dataset_download_files(
        dataset="olistbr/brazilian-ecommerce",
        path=str(RAW_DATA_DIR),
        unzip=True
    )
    print("E-Commerce dataset downloaded!")

def download_fraud_data():
    """Download Fraud Detection dataset from Kaggle."""
    print("Downloading Fraud Detection dataset...")
    kaggle.api.dataset_download_files(
        dataset="kartik2112/fraud-detection",
        path=str(RAW_DATA_DIR),
        unzip=True
    )
    print("Fraud dataset downloaded!")

if __name__ == "__main__":
    download_ecommerce_data()
    download_fraud_data()
    print("All datasets downloaded successfully!")