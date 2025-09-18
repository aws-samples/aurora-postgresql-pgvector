# Generative AI Use Cases with pgvector, Aurora PostgreSQL and Amazon Bedrock

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/aws-samples/aurora-postgresql-pgvector.svg)](https://github.com/aws-samples/aurora-postgresql-pgvector/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/aws-samples/aurora-postgresql-pgvector.svg)](https://github.com/aws-samples/aurora-postgresql-pgvector/network)
[![GitHub issues](https://img.shields.io/github/issues/aws-samples/aurora-postgresql-pgvector.svg)](https://github.com/aws-samples/aurora-postgresql-pgvector/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/aws-samples/aurora-postgresql-pgvector.svg)](https://github.com/aws-samples/aurora-postgresql-pgvector/pulls)
[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-yellow.svg)](https://spdx.org/licenses/MIT-0.html)

> Build powerful Generative AI applications using pgvector on Amazon Aurora PostgreSQL with Amazon Bedrock

## 🌟 Overview

This repository demonstrates sample implementations using [**pgvector**](https://github.com/pgvector/pgvector), a powerful PostgreSQL extension for vector similarity search, seamlessly integrated with Aurora PostgreSQL and Amazon Bedrock for building production-ready AI applications.

## 📚 Resources

### Documentation & Guides
- 📖 [AWS Blog: Leverage pgvector and Aurora PostgreSQL for NLP, Chatbots and Sentiment Analysis](https://aws.amazon.com/blogs/database/leverage-pgvector-and-amazon-aurora-postgresql-for-natural-language-processing-chatbots-and-sentiment-analysis/)
- 🚀 [AWS Blog: Supercharging Vector Search with pgvector 0.8.0](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)
- 🤖 [AWS Blog: Database Development with AWS MCP Servers](https://aws.amazon.com/blogs/database/supercharging-aws-database-development-with-aws-mcp-servers/)
- 🎓 [AWS Workshop: Complete Hands-on Labs](https://catalog.workshops.aws/pgvector/en-US)
- 🔧 [PostgreSQL MCP Server Documentation](https://awslabs.github.io/mcp/servers/postgres-mcp-server/)

## 🚀 Use Cases & Labs

### Core Implementations

| Module | Duration | Difficulty | Description |
|--------|----------|------------|-------------|
| **[Semantic Search & Sentiment Analysis](pgvector-similarity-search/)** | 45 min | 🟢 Beginner | Build a search engine that understands meaning and analyzes customer sentiment using Hugging Face models and Aurora ML |
| **[Product Recommendations](product-recommendations/)** | 45-60 min | 🟢 Beginner | Create a personalized product recommendation engine using Bedrock embeddings and similarity algorithms |
| **[Retrieval Augmented Generation (RAG)](retrieval-augmented-generation/)** | 45-60 min | 🟡 Intermediate | Implement a Q&A chatbot with accurate, grounded responses using RAG architecture |
| **[Text Summarization](text-summarization/)** | 45-60 min | 🟡 Intermediate | Build an automatic summarization system for large documents with key information extraction |

### Enterprise Solutions & Agents

| Module | Duration | Difficulty | Description |
|--------|----------|------------|-------------|
| **[Amazon Q Business Integration](amazon-q-business/)** | 45-60 min | 🟡 Intermediate | Deploy an AI-powered data exploration platform for healthcare data democratization |
| **[Aurora ML + Bedrock Movies](movie-recommendations/)** | 45-60 min | 🟡 Intermediate | Build a Netflix-style movie recommendation system using `aws_ml` extension |
| **[Bedrock Knowledge Bases](knowledge-bases/)** | 45-60 min | 🟡 Intermediate | Create enterprise knowledge bases for financial documents with regulatory compliance |
| **[Blaize Bazaar](blaize-bazaar/)** | 45-60 min | 🔴 Advanced | Deploy a complete e-commerce platform with AI-powered search and recommendations |
| **[Incident Detection & Remediation](incident-detection/)** | 45-60 min | 🔴 Advanced | Implement intelligent database monitoring with agentic workflows and auto-remediation using MCP servers |

## 🛠️ Getting Started

### Prerequisites
- AWS account with appropriate permissions
- Basic knowledge of PostgreSQL and Python
- 15-30 minutes for environment setup

### Quick Start

#### Option 1: AWS Workshop Studio (Recommended)
🔗 **[Launch Workshop](https://catalog.workshops.aws/pgvector/en-US)**

#### Option 2: Self-Paced Setup
```bash
git clone https://github.com/aws-samples/aurora-postgresql-pgvector.git
cd aurora-postgresql-pgvector

# Deploy infrastructure
aws cloudformation create-stack \
  --stack-name pgvector-workshop \
  --template-body file://cloudformation/genai-pgvector-lab.yml \
  --capabilities CAPABILITY_IAM
```

## 🗺️ Learning Paths

- **🌱 Beginners**: Start with Semantic Search → Product Recommendations → RAG
- **🚀 Advanced**: Jump to Blaize Bazaar → Incident Detection → MCP Servers
- **🎯 Targeted**: Choose specific labs based on your use case

## 🏗️ Architecture

### Core Technologies
- **Amazon Aurora PostgreSQL** with pgvector 0.8.0+
- **Amazon Bedrock** for foundation models
- **Amazon SageMaker** for ML hosting
- **AWS MCP Servers** for AI-database interactions
- **Amazon Bedrock Agents** for autonomous workflows

### Key Features
- ✅ Vector embeddings (up to 16,000 dimensions)
- ✅ HNSW and IVFFlat indexing
- ✅ Hybrid search capabilities
- ✅ RAG with streaming
- ✅ Multi-modal embeddings
- ✅ Agentic workflows

## 💻 Development Environment

Pre-configured Code Editor (VS Code in browser) includes:
- Python 3.11 with ML/AI libraries
- PostgreSQL client tools with pgvector
- AWS CLI and SDKs
- Jupyter notebook support
- Pre-installed AI development extensions

## 📄 License

This project is licensed under the [MIT-0 License](LICENSE) - see the LICENSE file for details.

## 📖 Additional Resources

- [pgvector Official Repository](https://github.com/pgvector/pgvector)
- [Amazon Aurora Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)
- [Amazon Bedrock Samples](https://github.com/aws-samples/amazon-bedrock-samples)
- [AWS MCP Servers](https://github.com/awslabs/mcp)

## ⚠️ Important Notes

- **Educational Purpose**: Sample code requiring adaptation for production use
- **Cost Management**: Running labs will incur AWS charges
- **Clean Up**: Always delete resources after completing labs

---

**Ready to start?** 🚀 **[Launch the Workshop](https://catalog.workshops.aws/pgvector/en-US)** | **[View Documentation](https://awslabs.github.io/mcp/servers/postgres-mcp-server/)**