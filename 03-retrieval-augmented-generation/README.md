# Retrieval Augmented Generation

This module contains three RAG examples that use Aurora PostgreSQL with pgvector as the retrieval store.

## Submodules

- `question-answering-opensource/`: Hugging Face embeddings and an open-source question-answering flow.
- `question-answering-bedrock/`: Amazon Bedrock embeddings and model selection through the Streamlit app.
- `response-streaming/`: Bedrock-backed RAG with streaming responses.

Each submodule has its own README, requirements file, sample data, and Streamlit entry point.

## Common Database Setup

Enable pgvector in the target Aurora PostgreSQL database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The Bedrock-backed apps read standard PostgreSQL environment variables:

```bash
PGUSER=<username>
PGPASSWORD=<password>
PGHOST=<aurora-cluster-endpoint>
PGPORT=5432
PGDATABASE=<database-name>
AWS_REGION=<aws-region>
```

The open-source app keeps the older `PGVECTOR_*` env names used by its LangChain integration.
