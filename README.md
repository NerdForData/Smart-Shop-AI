# Smart-Shop-AI

This repository contains code for Smart-Shop-AI. Data files are not stored in this repository to keep the repo small. Follow the steps below to download the required datasets locally.

## Data

Required datasets (from Kaggle):

- `olistbr/brazilian-ecommerce` (Brazilian ecommerce)
- `kartik2112/fraud-detection` (Fraud detection)

### Steps to download datasets

1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Get your Kaggle API token:
- Go to https://www.kaggle.com/ and sign in
- Visit **Account** → **API** → **Create New API Token**
- This downloads a `kaggle.json` file containing your username and key

3. Add credentials to the project (recommended project-scoped method):

- Create a `.env` file in the project root with the following content:

```text
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_key
```

The repository `.gitignore` already excludes `.env`, `data/`, and `datasets/`.

4. Download the datasets locally (saves to `datasets/` and `data/raw/`):

```bash
python ingestion/kaggle_downloader.py
```

This script uses the Kaggle API to download the datasets into `datasets/` and will organize CSVs under `data/raw/` for the pipeline.

If you prefer to use the CLI directly, you can instead place `kaggle.json` under `~/.kaggle/kaggle.json` and run:

```bash
kaggle datasets download -d olistbr/brazilian-ecommerce -p datasets/
kaggle datasets download -d kartik2112/fraud-detection -p datasets/
```

5. Run the cleaning pipeline:

```bash
python ingestion/data_cleaner.py
```

## BigQuery setup

To upload cleaned tables to BigQuery, add the following to your `.env` file:

```text
PROJECT_ID=smart-shop-ai-496616
BQ_DATASET=smartshop
# Optional: only set this if you use a service account JSON file
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

If you use a service account, set the variable either in `.env` or in your shell:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

If you prefer user authentication, log in with gcloud instead:

```bash
gcloud auth application-default login
```

Finally run:

```bash
python ingestion/bigquery_uploader.py
```

## Notes
- Large dataset files are intentionally excluded from git; do not add them to the repository.
- If you want to share datasets with collaborators, consider uploading them to cloud storage or a GitHub Release.
