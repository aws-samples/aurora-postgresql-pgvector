# AZFlights Valkey Chatbot

This module demonstrates semantic caching with Amazon Aurora PostgreSQL, pgvector, Amazon Bedrock, and ElastiCache for Valkey.

## Files

- `valkey-chatbot.py`: Streamlit chatbot app.
- `travel_knowledge_base.csv`: Precomputed 1536-dimensional travel embeddings.
- `load_travel_knowledge_base.py`: Loader for the Aurora PostgreSQL table used by the app.
- `env_sample`: Required environment variables.

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
    embedding vector(1536) NOT NULL,
    category text
);
```

The app defaults to `amazon.titan-embed-text-v1` for query embeddings so query vectors match the shipped 1536-dimensional CSV embeddings.
