# Product Recommendations with pgvector

This lab demonstrates two approaches for product similarity search and recommendations with Aurora PostgreSQL and pgvector.

## Notebooks

1. `opensource-similarity-search.ipynb`
   - Deploys Hugging Face `sentence-transformers/all-MiniLM-L6-v2` on SageMaker.
   - Generates 384-dimensional embeddings for the FEIDEGGER product image-description dataset.
   - Stores vectors in Aurora PostgreSQL and searches with pgvector.

2. `bedrock-similarity-search.ipynb`
   - Uses Amazon Bedrock Titan embeddings through `amazon.titan-embed-g1-text-02`.
   - Generates 1536-dimensional product-description embeddings.
   - Loads the Amazon product catalog from `data/amazon.csv`.
   - Creates an HNSW index and runs semantic product discovery queries.

## Setup

Install the notebook dependencies:

```bash
python3.9 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

You need:

- An AWS account with access to SageMaker for the open-source notebook.
- Bedrock model access for the Bedrock notebook.
- An Aurora PostgreSQL database with pgvector enabled.

Enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Notes

The two notebooks intentionally use different embedding dimensions. Keep the table schema aligned with the notebook you run: `vector(384)` for MiniLM and `vector(1536)` for Titan.
