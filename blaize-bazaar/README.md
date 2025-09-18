# Blaize Bazaar - Product Search with Bedrock Agent

This module contains labs for building an AI-powered e-commerce product search using:
- Amazon Aurora PostgreSQL with pgvector
- Amazon Bedrock Agents
- Streamlit for the web interface

## Source
Adapted from AWS DAT301 re:Invent 2024 workshop

## Labs Included
1. Data Ingestion to Aurora PostgreSQL
2. Product Catalog Search with Bedrock Agent
3. Text Summarization with Flan-T5
4. Intelligent Document Processing

## How to Use
1. Start with notebooks in order (01, 02, 03, 04)
2. Run the Streamlit app: `streamlit run Home.py`

## Configuration
Update the following for your environment:
- Secret Name: `apgpg-pgvector-secret`
- Stack Name: `genai-pgvector-labs-ProductSearchStack`
