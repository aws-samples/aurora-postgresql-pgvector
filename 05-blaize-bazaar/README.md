# Blaize Bazaar

Blaize Bazaar is the e-commerce demo module for Aurora PostgreSQL with pgvector and Amazon Bedrock. It includes notebooks for loading and searching a product catalog plus a Streamlit app with product insights, recommendations, Knowledge Bases, and Bedrock Agents pages.

## Included Notebooks

Run these from the `notebooks/` directory:

1. `Part 1_Building AI-Powered Semantic Product Search with pgvector and Amazon Bedrock.ipynb`
2. `Part 2_Building AI-Powered Semantic Product Search with pgvector and Amazon Bedrock - Part 2.ipynb`
3. `Part 3_Building AI-Powered Hybrid Product Search with pgvector and Amazon Bedrock - Part 2.ipynb`

## Run the App

```bash
cd 05-blaize-bazaar
python3 -m venv venv-blaize-bazaar
source venv-blaize-bazaar/bin/activate
pip install -r requirements.txt
streamlit run Home.py --server.port 8501
```

## Configuration

Copy `env.example` to `.env` and fill in the values produced by the workshop bootstrap or your own stack:

```bash
# Aurora PostgreSQL connection
DB_HOST=<aurora-cluster-endpoint>
DB_PORT=5432
DB_NAME=postgres
DB_USER=<database-username>
DB_PASSWORD=<database-password>

# AWS region — defaults to us-west-2 when unset
AWS_REGION=us-west-2

# Bedrock generation model (cross-region inference profile)
# global.anthropic.claude-sonnet-5 is also available as an override
BEDROCK_CLAUDE_MODEL_ID=global.anthropic.claude-sonnet-5

# Bedrock Knowledge Base ID (page 3)
BEDROCK_KB_ID=<knowledge-base-id>

# Bedrock Agent + Alias IDs (page 4)
BEDROCK_AGENT_ID=<agent-id>
BEDROCK_AGENT_ALIAS_ID=<agent-alias-id>

# S3 bucket backing the Knowledge Base (page 3 delete/re-sync)
S3_KB_BUCKET=<knowledge-base-s3-bucket-name>

# Lambda that triggers KB re-ingestion after S3 changes
LAMBDA_FUNCTION_NAME=genai-dat-301-labs_BedrockAgent_Lambda
```

The Knowledge Bases page (page 3) lets you reset the chat and trigger a re-sync of the Knowledge Base after deleting documents from S3; there is no document upload UI in the app. The Agents page (page 4) requires the Bedrock Agent to be deployed. Product Insights and Product Recommendations require the `bedrock_integration.product_catalog` table created by the notebooks or workshop setup.
