# Real-Time Document Intelligence with Streaming (Amazon Bedrock)

A RAG application with real-time streaming responses, powered by Amazon Bedrock and Aurora PostgreSQL with pgvector.

## Overview

- Amazon Bedrock (`us.anthropic.claude-haiku-4-5-20251001-v1:0` by default) for streaming generation
- Amazon Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`, 1024 dims) for embeddings
- Aurora PostgreSQL with pgvector for vector storage
- LangChain streaming callbacks for word-by-word response delivery
- Streamlit for the user interface

## Architecture

![Architecture](static/Streaming_Responses_RAG.png)

## Prerequisites

- Python 3.9 or higher
- An AWS account with **Amazon Bedrock model access** enabled. See [Request access to an Amazon Bedrock foundation model](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).
- An Amazon Aurora PostgreSQL cluster with the `vector` extension installed
- AWS credentials configured

## Installation

1. Clone the repository and navigate to this directory:
   ```bash
   git clone https://github.com/aws-samples/aurora-postgresql-pgvector.git
   cd aurora-postgresql-pgvector/03-retrieval-augmented-generation/response-streaming

   python3.11 -m venv env
   source env/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp env.example .env
   # Edit .env and fill in your values
   ```

   Key variables:
   ```
   PGUSER=<username>
   PGPASSWORD=<password>
   PGHOST=<aurora-cluster-endpoint>
   PGPORT=5432
   PGDATABASE=<database-name>
   AWS_REGION=us-west-2          # or your preferred region
   BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0   # optional override
   ```

   `global.anthropic.claude-sonnet-5` is also available as a `BEDROCK_MODEL_ID` override.

## Database Setup

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Running the Application

Preferred entry point:
```bash
streamlit run streaming_app.py
```

Alternative:
```bash
streamlit run app.py
```

Then upload PDF documents, click Process, and chat with your documents via streaming responses.

## License

[MIT-0 License](https://spdx.org/licenses/MIT-0.html)
