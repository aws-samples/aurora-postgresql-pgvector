# Generative AI Use Cases with pgvector, Aurora PostgreSQL, and Amazon Bedrock

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11.9-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Aurora PostgreSQL](https://img.shields.io/badge/Aurora-PostgreSQL-527FFF?style=for-the-badge&logo=amazonrds&logoColor=white)](https://aws.amazon.com/rds/aurora/)
[![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-FF9900?style=for-the-badge&logo=amazonwebservices&logoColor=white)](https://aws.amazon.com/bedrock/)
[![pgvector](https://img.shields.io/badge/pgvector-enabled-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![PostgreSQL Client](https://img.shields.io/badge/PostgreSQL-16_client-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

![License](https://img.shields.io/badge/License-MIT--0-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Educational-blue?style=for-the-badge)

</div>

This repository contains the hands-on labs for the **[Generative AI with pgvector and Aurora PostgreSQL Workshop](https://catalog.workshops.aws/pgvector/en-US)**. Each lab demonstrates a production-relevant use case for [pgvector](https://github.com/pgvector/pgvector) on Amazon Aurora PostgreSQL, integrated with Amazon Bedrock foundation models.

## Workshop Labs

| Lab                                                               | Module                                 | Difficulty   | Description                                                                                                            |
| ----------------------------------------------------------------- | -------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------- |
| [01 - Semantic Search](01-semantic-search/)                       | Semantic Search                        | Beginner     | Build a search engine that understands meaning using Hugging Face embeddings and Aurora PostgreSQL with pgvector       |
| [02 - Product Recommendations](02-product-recommendations/)       | Product Recommendations                | Beginner     | Create a personalized product recommendation engine using Bedrock embeddings and similarity algorithms                 |
| [03 - RAG](03-retrieval-augmented-generation/)                    | Retrieval Augmented Generation         | Intermediate | Implement a Q&A chatbot with accurate, grounded responses using RAG architecture                                       |
| [04 - Movie Recommendations](04-aurora-ml-movie-recommendations/) | Aurora ML with Bedrock                 | Intermediate | Build a movie recommendation system using the `aws_ml` extension for in-database inference                             |
| [05 - Blaize Bazaar](05-blaize-bazaar/)                           | E-Commerce Platform                    | Advanced     | Deploy a complete e-commerce platform with AI-powered search and recommendations                                       |
| [06 - Incident Detection](06-incident-detection/)                 | Incident Detection and Remediation     | Advanced     | Implement intelligent database monitoring with agentic workflows and auto-remediation                                  |
| [07 - Aurora ML Chatbot](07-aurora-ml-chatbot/)                   | Aurora ML Chatbot                      | Intermediate | Build an AI-powered chatbot that runs inference directly within the database using Aurora ML                           |
| [08 - Valkey Chatbot](08-valkey-chatbot/)                         | Caching with ElastiCache for Valkey    | Intermediate | Build a travel chatbot with semantic caching using Aurora PostgreSQL and ElastiCache for Valkey                        |

## Suggested Learning Paths

- **Getting Started**: Labs 01 → 02 → 03 cover the fundamentals of vector search, embeddings, and RAG.
- **Advanced Patterns**: Labs 05 and 06 explore production-scale architectures with agentic workflows.
- **Targeted**: Each lab is self-contained — pick the use case most relevant to your needs.

## Getting Started

### Prerequisites

- AWS account with appropriate permissions
- Basic knowledge of PostgreSQL and Python
- 15–30 minutes for environment setup

### Option 1: AWS Workshop Studio (Recommended)

Follow the guided experience at **[catalog.workshops.aws/pgvector](https://catalog.workshops.aws/pgvector/en-US)**, which provides a pre-configured AWS environment with all dependencies installed.

### Option 2: Self-Paced Setup

```bash
git clone https://github.com/aws-samples/aurora-postgresql-pgvector.git
cd aurora-postgresql-pgvector
```

Refer to each lab's README for specific setup instructions and dependencies.

## Architecture Overview

### Core Technologies

- **Amazon Aurora PostgreSQL** with the pgvector extension
- **Amazon Bedrock** for foundation models (Titan, Claude)
- **Amazon SageMaker** for ML model hosting
- **Amazon Bedrock Agents** for autonomous workflows

### Key Capabilities

- Vector embeddings (up to 16,000 dimensions)
- HNSW and IVFFlat indexing for approximate nearest neighbor search
- Hybrid search (vector + full-text)
- RAG with response streaming
- In-database ML inference via Aurora ML
- Agentic workflows with auto-remediation

## Development Environment

The workshop's Code Editor (VS Code in browser) comes pre-configured with:

- Python 3.11.9 with ML/AI libraries
- PostgreSQL client tools with pgvector
- AWS CLI and SDKs
- Jupyter notebook support

## Resources

- [AWS Blog: Leverage pgvector and Aurora PostgreSQL for NLP, Chatbots and Sentiment Analysis](https://aws.amazon.com/blogs/database/leverage-pgvector-and-amazon-aurora-postgresql-for-natural-language-processing-chatbots-and-sentiment-analysis/)
- [AWS Blog: Supercharging Vector Search with pgvector 0.8.0](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [pgvector Official Repository](https://github.com/pgvector/pgvector)
- [Amazon Aurora Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)

## Important Notes

- This repository is intended for educational purposes. Sample code should be adapted before production use.
- Running these labs will incur AWS charges. Always clean up resources after completing a lab.

## License

<div align="center">

This project is licensed under the [MIT-0 License](LICENSE).

[![Powered by AWS](https://img.shields.io/badge/Powered_by-AWS-FF9900?style=flat&logo=amazonwebservices)](https://aws.amazon.com)

</div>
