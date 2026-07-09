# Generative AI Use Cases with pgvector, Aurora PostgreSQL, and Amazon Bedrock

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Aurora PostgreSQL](https://img.shields.io/badge/Aurora-PostgreSQL-527FFF?style=for-the-badge&logo=amazonrds&logoColor=white)](https://aws.amazon.com/rds/aurora/)
[![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-FF9900?style=for-the-badge&logo=amazonwebservices&logoColor=white)](https://aws.amazon.com/bedrock/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2B-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)

![License](https://img.shields.io/badge/License-MIT--0-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Educational-blue?style=for-the-badge)

</div>

This repository contains the hands-on labs for the **[Generative AI with pgvector and Aurora PostgreSQL Workshop](https://catalog.workshops.aws/pgvector/en-US)**. The labs build from vector-search fundamentals into retrieval augmented generation, in-database ML inference, semantic caching, and agentic operational patterns.

Use the hosted Workshop Studio experience when you want the fastest path through the labs. Use the self-paced path when you want to inspect the implementation, adapt the code, or run individual modules in your own AWS account.

## What You Will Build

- Semantic search over structured and unstructured content with Aurora PostgreSQL and pgvector.
- Product and movie recommendation flows powered by embeddings and similarity search.
- RAG applications that retrieve context from Aurora PostgreSQL and generate answers with Amazon Bedrock.
- Streamlit apps, notebooks, and Lambda functions that show how these patterns fit into real application workflows.
- Operational examples for incident analysis, remediation, and semantic caching.

## Workshop Labs

| Lab | Focus | You build | Primary services |
| --- | --- | --- | --- |
| [01 - Semantic Search](01-semantic-search/) | Vector search basics | Hotel-review semantic search with Hugging Face embeddings | Aurora PostgreSQL, pgvector |
| [02 - Product Recommendations](02-product-recommendations/) | Similarity search | Product discovery and recommendations with open-source and Bedrock embeddings | Aurora PostgreSQL, pgvector, Amazon Bedrock, SageMaker |
| [03 - RAG](03-retrieval-augmented-generation/) | Retrieval augmented generation | Q&A apps that retrieve context from pgvector and generate grounded responses | Aurora PostgreSQL, Amazon Bedrock, Streamlit |
| [04 - Movie Recommendations](04-aurora-ml-movie-recommendations/) | Aurora ML | Movie recommendations using in-database calls to Bedrock-backed ML functions | Aurora PostgreSQL, Aurora ML, Amazon Bedrock |
| [05 - Blaize Bazaar](05-blaize-bazaar/) | E-commerce app patterns | A catalog experience with semantic search, product insights, and recommendations | Aurora PostgreSQL, Amazon Bedrock, Streamlit |
| [06 - Incident Detection](06-incident-detection/) | Operations and agents | Incident analysis, alert retrieval, and remediation workflows | Aurora PostgreSQL, Lambda, API Gateway, Bedrock Agents |
| [07 - Aurora ML Chatbot](07-aurora-ml-chatbot/) | In-database chatbot | A chatbot that performs embedding search and generation from database-side functions | Aurora PostgreSQL, Aurora ML, Amazon Bedrock |
| [08 - Valkey Chatbot](08-valkey-chatbot/) | Semantic caching | A travel chatbot with Aurora-backed retrieval and Valkey-backed response caching | Aurora PostgreSQL, ElastiCache for Valkey, Amazon Bedrock |

## Choose a Path

| Path | Best for | Start here |
| --- | --- | --- |
| Hosted workshop | Guided delivery with a pre-provisioned environment | [catalog.workshops.aws/pgvector](https://catalog.workshops.aws/pgvector/en-US) |
| Self-paced local review | Reading code, adapting modules, or running selected labs yourself | Clone this repo and follow the README in each lab directory |

### Recommended Lab Order

- **Foundations:** `01 -> 02 -> 03`
- **In-database inference:** `04 -> 07`
- **Application patterns:** `05 -> 08`
- **Operations and agents:** `06`

Each lab is intentionally scoped so you can run it independently after the required AWS resources and environment variables are in place.

## Self-Paced Setup

```bash
git clone https://github.com/aws-samples/aurora-postgresql-pgvector.git
cd aurora-postgresql-pgvector
```

You will need:

- An AWS account with permissions for the services used by the selected lab.
- Amazon Bedrock model access for labs that generate embeddings or text.
- Access to an Aurora PostgreSQL cluster with the `vector` extension enabled.
- Python 3.11+ and PostgreSQL client tools.

Most labs include their own `requirements.txt`, `.env` example, notebook, or Streamlit app. Start with the README in the lab directory you want to run.

## Core Patterns

- **Vector search:** Store embeddings in Aurora PostgreSQL and query them with pgvector similarity operators and HNSW indexes.
- **Hybrid retrieval:** Combine semantic search with structured metadata and application-specific filters.
- **RAG:** Retrieve relevant context from the database before calling a foundation model.
- **Aurora ML:** Invoke ML and Bedrock-backed functions from SQL when database-local inference is useful.
- **Semantic caching:** Use embedding similarity to reuse prior responses when a new query is close enough.
- **Agentic workflows:** Connect alerts, runbooks, and remediation actions into operational flows.

## Model and Embedding Standards

- **Embeddings:** Amazon Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`, 1024 dimensions). Vector columns are `vector(1024)`.
- **Generation:** Claude Sonnet 5 via Bedrock cross-region inference profiles (`global.anthropic.claude-sonnet-5`). Each lab reads the model ID from the `BEDROCK_MODEL_ID` environment variable (or the lab-specific equivalent) so you can override it at runtime. `global.anthropic.claude-sonnet-5` is also available as an override.

## Development Environment

The hosted workshop environment is pre-configured with:

- Python 3.11+ with the required ML and application libraries.
- PostgreSQL 18 client tools.
- AWS CLI and AWS SDKs.
- Jupyter notebook and Streamlit support.

For local or self-managed environments, install dependencies per lab instead of installing every requirements file at the repo root.

## Security and Cost Notes

- This is educational sample code. Review authentication, authorization, networking, logging, and data-handling choices before adapting it for production.
- Running the labs can create billable AWS resources. Clean up the resources for each lab when you are finished.
- Keep dependency updates targeted and validated because each lab has its own runtime and dependency set.

## Resources

- [Workshop: Generative AI with pgvector and Aurora PostgreSQL](https://catalog.workshops.aws/pgvector/en-US)
- [AWS Blog: Leverage pgvector and Aurora PostgreSQL for NLP, Chatbots and Sentiment Analysis](https://aws.amazon.com/blogs/database/leverage-pgvector-and-amazon-aurora-postgresql-for-natural-language-processing-chatbots-and-sentiment-analysis/)
- [AWS Blog: Supercharging Vector Search with pgvector 0.8.0](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [pgvector Official Repository](https://github.com/pgvector/pgvector)
- [Amazon Aurora Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)

## License

<div align="center">

This project is licensed under the [MIT-0 License](LICENSE).

[![Powered by AWS](https://img.shields.io/badge/Powered_by-AWS-FF9900?style=flat&logo=amazonwebservices)](https://aws.amazon.com)

</div>
