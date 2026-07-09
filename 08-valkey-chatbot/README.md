# AZFlights Valkey Chatbot

This module demonstrates semantic caching with Amazon Aurora PostgreSQL, pgvector, Amazon Bedrock, and ElastiCache for Valkey.

## Files

- `valkey-chatbot.py`: Streamlit chatbot app.
- `travel_knowledge_base.csv`: Precomputed 1024-dimensional travel embeddings (Titan Embeddings V2).
- `load_travel_knowledge_base.py`: Loader for the Aurora PostgreSQL table used by the app.
- `env_sample`: Required environment variables.

## Prerequisites

### Amazon Bedrock model access

Enable the following models in the Bedrock console (us-west-2 or your chosen region) before running:

- **Amazon Titan Embeddings V2** (`amazon.titan-embed-text-v2:0`) — used to embed user queries at chat time.
- **Anthropic Claude Haiku 4.5** (`us.anthropic.claude-haiku-4-5-20251001-v1:0`, cross-region inference profile) — used to generate responses. Override via `BEDROCK_MODEL_ID` (e.g., set `global.anthropic.claude-sonnet-5` for higher quality).

### ElastiCache for Valkey

The app connects to a Valkey-compatible ElastiCache cluster over TLS. Find your cluster's primary endpoint in the ElastiCache console and set `ELASTICACHE_HOST` to that value (without the port). If the endpoint is unreachable the app degrades gracefully: chat still works but semantic caching, chat history, and user preferences are disabled.

## Setup

```bash
cd 08-valkey-chatbot
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
cp env_sample .env
```

Fill in `.env`, then load the knowledge base:

```bash
python load_travel_knowledge_base.py --truncate
```

Run the app:

```bash
streamlit run valkey-chatbot.py --server.port 8501
```

## Database Schema

The loader creates:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS travel_knowledge_base (
    id integer PRIMARY KEY,
    content text NOT NULL,
    embedding vector(1024) NOT NULL,
    category text
);

CREATE INDEX IF NOT EXISTS travel_kb_embedding_hnsw_idx
    ON travel_knowledge_base USING hnsw (embedding vector_cosine_ops);
```

The HNSW index uses cosine distance (`<=>` operator) for fast approximate nearest-neighbour lookup.

## Knowledge base embeddings

`travel_knowledge_base.csv` ships with embeddings already computed using `amazon.titan-embed-text-v2:0` at 1024 dimensions. Do **not** use `amazon.titan-embed-text-v1` (1536-dim) — the precomputed vectors will not match.

To regenerate the knowledge base from scratch:

1. Embed column 2 (the `content` column) of the CSV via `amazon.titan-embed-text-v2:0` with `"dimensions": 1024, "normalize": true` in the invoke-model body.
2. Write the resulting float list back to column 3.
3. Re-run `load_travel_knowledge_base.py --truncate`.

## Semantic cache flow

When a user submits a query the app:

1. Generates a 1024-dim embedding for the query text (Bedrock, Titan v2).
2. Checks Valkey for a cached vector-search result keyed by a SHA-256 hash of the normalised query text (**cache hit** — sub-millisecond retrieval).
3. On a cache miss, queries Aurora PostgreSQL with the `<=>` cosine operator and caches the result in Valkey (TTL 1 hour).
4. Passes the retrieved context plus the user's stored preferences and chat history to the generation model and streams the response.

The sidebar shows live hit/miss counters and average retrieval latencies so you can observe the speedup on repeated queries.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | (required) | Aurora PostgreSQL endpoint |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | (required) | Database name |
| `DB_USER` | (required) | Database user |
| `DB_PASSWORD` | (required) | Database password |
| `AWS_REGION` | `us-west-2` | AWS region for Bedrock API calls |
| `ELASTICACHE_HOST` | (required) | ElastiCache primary endpoint (no port) |
| `ELASTICACHE_PORT` | `6379` | ElastiCache port |
| `BEDROCK_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Bedrock embedding model |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Bedrock generation model — override with e.g. `global.anthropic.claude-sonnet-5` |
