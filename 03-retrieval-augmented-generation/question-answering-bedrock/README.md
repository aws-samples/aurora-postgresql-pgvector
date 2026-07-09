# Enterprise RAG Question-Answering System (Amazon Bedrock)

Build a Retrieval Augmented Generation (RAG) application powered by Amazon Bedrock and Aurora PostgreSQL with pgvector.

## Overview

- Amazon Bedrock for foundation model access (Claude Sonnet 5, Amazon Nova Micro/Lite/Pro)
- Aurora PostgreSQL with pgvector for vector storage
- Amazon Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`) for generating embeddings
- LangChain for the retrieval pipeline
- Streamlit for the user interface

## Architecture

![Architecture](static/RAG_APG.png)

## Prerequisites

- Python 3.9 or higher
- An AWS account with **Amazon Bedrock model access** enabled for the models you want to use. See [Request access to an Amazon Bedrock foundation model](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).
- An Amazon Aurora PostgreSQL cluster with the `vector` extension installed
- AWS credentials configured (IAM role, `aws configure`, or environment variables)

## Installation

1. Clone the repository and navigate to this directory:
   ```bash
   git clone https://github.com/aws-samples/aurora-postgresql-pgvector.git
   cd aurora-postgresql-pgvector/03-retrieval-augmented-generation/question-answering-bedrock
   ```

2. Create and activate a virtual environment:
   ```bash
   python3.13 -m venv env
   source env/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
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
   BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-5   # optional override
   ```

   `global.anthropic.claude-sonnet-5` is also available as a `BEDROCK_MODEL_ID` override.

## Database Setup

Connect to your Aurora PostgreSQL cluster and enable the pgvector extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Running the Application

Preferred entry point (bootstraps runtime and then calls `app.main()`):
```bash
streamlit run rag_app.py
```

Alternative (runs the same app via `__main__` block):
```bash
streamlit run app.py
```

Then navigate to the web interface, upload PDF documents, and start asking questions.

## Model Selection

The sidebar lets you choose between:

| Display name | Model ID |
|---|---|
| Claude Sonnet 5 | `global.anthropic.claude-sonnet-5` (or `BEDROCK_MODEL_ID`) |
| Amazon Nova Micro | `us.amazon.nova-micro-v1:0` |
| Amazon Nova Lite | `us.amazon.nova-lite-v1:0` |
| Amazon Nova Pro | `us.amazon.nova-pro-v1:0` |

All Nova cross-region `us.*` profiles work in us-west-2 and other supported regions.

## License

[MIT-0 License](https://spdx.org/licenses/MIT-0.html)
