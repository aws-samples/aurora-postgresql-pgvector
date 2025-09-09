# Generative AI Use Cases with pgvector, Aurora PostgreSQL and Amazon Bedrock

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/aws-samples/aurora-postgresql-pgvector.svg)](https://github.com/aws-samples/aurora-postgresql-pgvector/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/aws-samples/aurora-postgresql-pgvector.svg)](https://github.com/aws-samples/aurora-postgresql-pgvector/network)
[![GitHub issues](https://img.shields.io/github/issues/aws-samples/aurora-postgresql-pgvector.svg)](https://github.com/aws-samples/aurora-postgresql-pgvector/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/aws-samples/aurora-postgresql-pgvector.svg)](https://github.com/aws-samples/aurora-postgresql-pgvector/pulls)
[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-yellow.svg)](https://spdx.org/licenses/MIT-0.html)

> Explore powerful Generative AI applications using pgvector on Amazon Aurora PostgreSQL with Amazon Bedrock

## 🌟 Overview

This repository demonstrates sample code implementations using [**pgvector**](https://github.com/pgvector/pgvector), a powerful open-source PostgreSQL extension for vector similarity search. pgvector seamlessly integrates with PostgreSQL's native features, enabling sophisticated vector operations, indexing, and querying capabilities.

## 📚 Resources

### Documentation & Guides
- 📖 [AWS Blog: Leverage pgvector and Amazon Aurora PostgreSQL for NLP, Chatbots and Sentiment Analysis](https://aws.amazon.com/blogs/database/leverage-pgvector-and-amazon-aurora-postgresql-for-natural-language-processing-chatbots-and-sentiment-analysis/)
- 🚀 [AWS Blog: Supercharging Vector Search Performance with pgvector 0.8.0](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)
- 🤖 [AWS Blog: Supercharging Database Development with AWS MCP Servers](https://aws.amazon.com/blogs/database/supercharging-aws-database-development-with-aws-mcp-servers/)
- 🎓 [AWS Workshop: Generative AI Use Cases with Aurora PostgreSQL and pgvector](https://catalog.workshops.aws/pgvector/en-US)
- 🔧 [PostgreSQL MCP Server Documentation](https://awslabs.github.io/mcp/servers/postgres-mcp-server/)

## 🚀 Use Cases

This repository showcases the following sample code implementations:

1. **Product Recommendations** 🛍️
   - Implement intelligent product recommendation systems
   - Leverage vector similarity for personalized suggestions

2. **Retrieval Augmented Generation (RAG)** 📄
   - Enhance LLM responses with relevant context
   - Implement efficient vector-based information retrieval

3. **Semantic Search and Sentiment Analysis** 🔍
   - Deploy sophisticated natural language search capabilities
   - Perform nuanced sentiment analysis on text data

4. **Knowledge Bases for Amazon Bedrock** 📚
   - Build scalable knowledge management systems
   - Integrate with Amazon Bedrock for enhanced AI capabilities

5. **Movie Recommendations** 🎬
   - Implement ML-based movie recommendation systems
   - Combine Aurora ML with Amazon Bedrock for sophisticated predictions

6. **Democratizing Data Insights with Amazon Q Business** 💼
   - Connect Amazon Q Business with Aurora PostgreSQL for enterprise-wide data access
   - Implement secure data exploration through user management and access control lists (ACLs)

7. **Intelligent Agents & MCP Servers** 🤖
   - Build agentic workflows for autonomous database operations
   - Leverage Model Context Protocol servers for enhanced AI-database interactions
   - Implement automated incident detection and remediation

## 🛠️ Getting Started

### Prerequisites

Before starting the workshop, ensure you have:
- An AWS account with appropriate permissions
- Basic knowledge of PostgreSQL and Python
- Understanding of machine learning concepts (helpful but not required)
- 15-30 minutes for initial environment setup

### Quick Start Options

#### Option 1: AWS Workshop Studio (Recommended)
Access the complete guided workshop with pre-configured environments:

🔗 **[Launch Workshop](https://catalog.workshops.aws/pgvector/en-US)**

#### Option 2: Self-Paced Setup

1. Clone the repository:
```bash
git clone https://github.com/aws-samples/aurora-postgresql-pgvector.git
cd aurora-postgresql-pgvector
```

2. Deploy the infrastructure:
```bash
# Review and customize parameters in the CloudFormation templates
aws cloudformation create-stack \
  --stack-name pgvector-workshop \
  --template-body file://static/genai-pgvector-labs.yml \
  --capabilities CAPABILITY_IAM
```

3. Follow the setup instructions in each lab directory

## 🗺️ Learning Paths

### 🌱 **Beginner Path** (New to Vector Embeddings)
**Recommended sequence:** Semantic Search → Product Recommendations → RAG
- Start with fundamental concepts of vector similarity
- Build progressively complex applications
- Estimated time: 3-4 hours

### 🚀 **Advanced Path** (Experienced with AI/ML)
**Recommended sequence:** Bedrock Knowledge Bases → Blaize Bazaar → IDR with Agents
- Jump into enterprise-grade implementations
- Focus on advanced patterns and agent architectures
- Estimated time: 3-4 hours

### 🎯 **Targeted Learning** (Specific Use Case)
Choose the lab that best matches your needs from our comprehensive catalog below.

## 📚 Workshop Modules

### Core Learning Labs

| Module | Duration | Difficulty | Description |
|--------|----------|------------|-------------|
| **[Semantic Search & Sentiment Analysis](https://catalog.workshops.aws/pgvector/en-US/2-semantic-search-and-sentiment-analysis)** | 45 min | 🟢 Beginner | Build a search engine that understands meaning and analyzes customer sentiment using Hugging Face models and Aurora ML |
| **[Product Recommendations](https://catalog.workshops.aws/pgvector/en-US/3-product-recommendations)** | 45-60 min | 🟢 Beginner | Create a personalized product recommendation engine using Bedrock embeddings and similarity algorithms |
| **[Retrieval Augmented Generation (RAG)](https://catalog.workshops.aws/pgvector/en-US/4-retrieval-augmented-generation)** | 45-60 min | 🟡 Intermediate | Implement a Q&A chatbot with accurate, grounded responses using RAG architecture |
| **[Text Summarization](https://catalog.workshops.aws/pgvector/en-US/5-text-summarization)** | 45-60 min | 🟡 Intermediate | Build an automatic summarization system for large documents with key information extraction |

### Enterprise Solutions & Agents

| Module | Duration | Difficulty | Description |
|--------|----------|------------|-------------|
| **[Amazon Q Business Integration](https://catalog.workshops.aws/pgvector/en-US/6-amazon-q-business-democratizing-organizational-data-insights)** | 45-60 min | 🟡 Intermediate | Deploy an AI-powered data exploration platform for healthcare data democratization |
| **[Aurora ML + Bedrock Movies](https://catalog.workshops.aws/pgvector/en-US/7-aurora-ml-and-amazon-bedrock-movie-recommendations)** | 45-60 min | 🟡 Intermediate | Build a Netflix-style movie recommendation system using `aws_ml` extension |
| **[Bedrock Knowledge Bases](https://catalog.workshops.aws/pgvector/en-US/8-bedrock-knowledge-bases)** | 45-60 min | 🟡 Intermediate | Create enterprise knowledge bases for financial documents with regulatory compliance |
| **[Blaize Bazaar](https://catalog.workshops.aws/pgvector/en-US/9-blaize-bazaar)** | 45-60 min | 🔴 Advanced | Deploy a complete e-commerce platform with AI-powered search and recommendations |
| **[Incident Detection & Remediation](https://catalog.workshops.aws/pgvector/en-US/10-incident-detection-and-remediation)** | 45-60 min | 🔴 Advanced | Implement intelligent database monitoring with agentic workflows and auto-remediation using MCP servers |

## 🏗️ Architecture Components

### Core Technologies
- **Amazon Aurora PostgreSQL** - Scalable, highly available relational database with pgvector 0.8.0+
- **pgvector Extension** - Advanced vector similarity search with HNSW and IVFFlat indexing
- **Amazon Bedrock** - Fully managed foundation models for generative AI
- **Amazon SageMaker** - Machine learning platform for model hosting and inference
- **AWS MCP Servers** - Model Context Protocol servers for enhanced AI-database interactions
- **Amazon Bedrock Agents** - Orchestrate complex multi-step tasks autonomously

### Key Features Demonstrated
- ✅ Vector embeddings with pgvector (up to 16,000 dimensions)
- ✅ HNSW and IVFFlat indexing for similarity search
- ✅ Hybrid search (vector + keyword matching)
- ✅ RAG pattern implementation with streaming
- ✅ Multi-modal embeddings (text, images, documents)
- ✅ Agentic workflows and MCP server integration
- ✅ Enterprise deployment patterns with security best practices

## 💻 Development Environment

The workshop includes a pre-configured **Code Editor** (VS Code in browser) with:
- Python 3.11 with essential ML/AI libraries (NumPy, Pandas, Scikit-learn)
- PostgreSQL 15+ client tools with pgvector support
- AWS CLI and SDKs pre-configured
- Jupyter notebook support for interactive development
- Pre-installed extensions for AWS services and AI development
- MCP server tools for database interactions

## 🔒 Security & Compliance

- **Authentication**: IAM-based database authentication
- **Secrets Management**: AWS Secrets Manager integration
- **Network Security**: VPC endpoints for private connectivity
- **Encryption**: At-rest and in-transit encryption
- **Access Control**: Fine-grained IAM policies and database roles
- **Audit**: CloudTrail and database activity monitoring
- **Compliance**: HIPAA, PCI-DSS, SOC 2 ready configurations

## 🤖 Agents & MCP Servers

### Intelligent Agents
Learn to build autonomous agents that can:
- Monitor database performance and auto-remediate issues
- Orchestrate complex multi-step workflows
- Make intelligent decisions based on real-time data
- Interact with multiple AWS services seamlessly

### Model Context Protocol (MCP) Servers
Leverage MCP servers for:
- Enhanced AI-database interactions
- Standardized tool interfaces for LLMs
- Efficient context management
- Seamless integration with Claude and other AI assistants

Learn more: [PostgreSQL MCP Server Documentation](https://awslabs.github.io/mcp/servers/postgres-mcp-server/)

## 🤝 Contributing

This repository is maintained for educational purposes and does not accept external contributions. However, you are encouraged to:
- Fork the repository for your own use
- Adapt the code for your specific needs
- Share your learnings with the community
- Report issues or suggest improvements

## 📄 License

This project is licensed under the [MIT-0 License](https://spdx.org/licenses/MIT-0.html) - see the [LICENSE](LICENSE) file for details.

## 📖 Additional Resources

### Related Projects
- [pgvector Official Repository](https://github.com/pgvector/pgvector)
- [Amazon Aurora Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)
- [Amazon Bedrock Samples](https://github.com/aws-samples/amazon-bedrock-samples)
- [AWS MCP Servers](https://github.com/awslabs/mcp)

### Community & Support
- **Workshop Issues**: Check troubleshooting sections in each lab
- **Bug Reports**: [Open an issue](https://github.com/aws-samples/aurora-postgresql-pgvector/issues)
- **Feedback**: [Email us](mailto:pgvector-usecase@amazon.com)
- **AWS Support**: Available through your AWS account

## ⚠️ Important Notes

- **Educational Purpose**: This repository is for learning and demonstration
- **Sample Code**: These are examples requiring adaptation and testing for production use
- **Cost Management**: Running these labs will incur AWS charges
- **Clean Up**: Always clean up resources after completing labs to avoid unnecessary costs

## 🎯 Learning Outcomes

Upon completing this workshop, you will be able to:
- ✅ Design and implement high-performance vector search systems
- ✅ Build RAG applications with streaming capabilities
- ✅ Deploy AI-powered recommendation engines at scale
- ✅ Create intelligent agents with autonomous capabilities
- ✅ Integrate MCP servers for enhanced database operations
- ✅ Optimize vector database performance with pgvector 0.8.0
- ✅ Implement enterprise security best practices for AI applications
- ✅ Orchestrate complex multi-step workflows with agents

---

**Ready to start?** Head to the [Prerequisites](/1-introduction/c-prerequisites) and let's begin your journey into building AI-powered applications with Aurora PostgreSQL! 🚀

**[Launch the Workshop](https://catalog.workshops.aws/pgvector/en-US)** | **[View Prerequisites](/1-introduction/c-prerequisites)** | **[Explore MCP Servers](https://awslabs.github.io/mcp/servers/postgres-mcp-server/)**
