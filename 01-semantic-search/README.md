# Semantic Search with pgvector and LangChain

This lab builds semantic search over hotel reviews using Aurora PostgreSQL with pgvector, LangChain, and Hugging Face embeddings.

## What This Lab Uses

- Aurora PostgreSQL with the `vector` extension
- LangChain's PostgreSQL vector store integration
- Hugging Face `sentence-transformers/all-mpnet-base-v2`
- The sample hotel reviews in `data/fictitious_hotel_reviews_trimmed_500.csv`
- The notebook `pgvector_langchain_auroraml.ipynb`

The notebook generates 768-dimensional embeddings and stores them in pgvector for similarity search.

## Setup

Create a Python environment and install both requirement files:

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements1.txt -r requirements2.txt
```

Create `.env` from `env.example` and fill in your Aurora PostgreSQL connection values:

```bash
cp env.example .env
```

Enable pgvector in your target database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Open and run:

```text
pgvector_langchain_auroraml.ipynb
```

## AWS Model Access

This lab uses only Hugging Face `sentence-transformers/all-mpnet-base-v2` for embeddings, downloaded locally via the `sentence-transformers` package. No Amazon Bedrock model access is required.

## Troubleshooting

If you see a vector dimension mismatch, check the table schema against the embedding model. This lab uses `all-mpnet-base-v2`, which returns 768-dimensional embeddings.

## Security Note

Keep database credentials in `.env` or your workshop environment. Do not commit local `.env` files.
