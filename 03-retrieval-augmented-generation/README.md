# Retrieval Augmented Generation

This module contains three RAG examples that use Aurora PostgreSQL with pgvector as the retrieval store.

## Submodules

- `question-answering-opensource/` — Hugging Face embeddings and an open-source question-answering flow. Entry point: `streamlit run app.py`
- `question-answering-bedrock/` — Amazon Bedrock embeddings and model selection (Claude Sonnet 5, Amazon Nova) through the Streamlit app. Entry points: `streamlit run rag_app.py` (recommended) or `streamlit run app.py`
- `response-streaming/` — Bedrock-backed RAG with streaming responses. Entry points: `streamlit run streaming_app.py` (recommended) or `streamlit run app.py`

## Shared Code

`rag_shared.py` and `htmlTemplates.py` at this directory level are shared by all three apps. Each app adds `..` to `sys.path` at startup so these are importable without installation.

## Common Database Setup

Enable pgvector in the target Aurora PostgreSQL database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Prerequisites

- Python 3.9 or higher
- An AWS account with **Amazon Bedrock model access** enabled for the models you plan to use (see [Request access to an Amazon Bedrock foundation model](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html))
- An Amazon Aurora PostgreSQL cluster with the `vector` extension installed
- For the opensource app: a Hugging Face account and API token

## Environment Setup

Each submodule ships an `env.example`. Copy it and fill in your values:

```bash
cp env.example .env
# then edit .env
```

The Bedrock-backed apps read standard PostgreSQL environment variables:

```
PGUSER=<username>
PGPASSWORD=<password>
PGHOST=<aurora-cluster-endpoint>
PGPORT=5432
PGDATABASE=<database-name>
AWS_REGION=<aws-region>          # defaults to us-west-2
BEDROCK_MODEL_ID=<model-id>      # optional override; see app README
```

The open-source app also accepts the older `PGVECTOR_*` env names.

## Model IDs

| Use | Default model ID |
|-----|-----------------|
| Generation (bedrock app) | `global.anthropic.claude-sonnet-5` (override: `global.anthropic.claude-sonnet-5`) |
| Generation (streaming app) | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| Embeddings | `amazon.titan-embed-text-v2:0` (1024 dimensions) |

Override the generation model by setting `BEDROCK_MODEL_ID` in your `.env`.
