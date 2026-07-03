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

Create `.env` with the values produced by the workshop bootstrap or your own stack:

```bash
DB_HOST=<aurora-endpoint>
DB_PORT=5432
DB_NAME=postgres
DB_USER=<database-user>
DB_PASSWORD=<database-password>
AWS_REGION=<aws-region>
BEDROCK_CLAUDE_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
BEDROCK_KB_ID=<knowledge-base-id>
BEDROCK_AGENT_ID=<agent-id>
BEDROCK_AGENT_ALIAS_ID=<agent-alias-id>
S3_KB_BUCKET=<knowledge-base-bucket>
```

The Knowledge Bases and Agents pages require the corresponding Bedrock resources. Product Insights and Product Recommendations require the `bedrock_integration.product_catalog` table created by the notebooks or workshop setup.
