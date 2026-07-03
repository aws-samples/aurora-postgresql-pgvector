import os

import boto3
from dotenv import load_dotenv
from langchain_community.embeddings import BedrockEmbeddings

import app as app_module


def configure_runtime():
    load_dotenv()

    aws_region = os.getenv("AWS_REGION", "us-west-2")
    app_module.BEDROCK_CLIENT = boto3.client("bedrock-runtime", aws_region)
    app_module.embeddings = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        client=app_module.BEDROCK_CLIENT,
    )

    db_user = os.getenv("PGUSER") or os.getenv("PGVECTOR_USER")
    db_password = os.getenv("PGPASSWORD") or os.getenv("PGVECTOR_PASSWORD")
    db_host = os.getenv("PGHOST") or os.getenv("PGVECTOR_HOST")
    db_port = os.getenv("PGPORT") or os.getenv("PGVECTOR_PORT") or "5432"
    db_name = os.getenv("PGDATABASE") or os.getenv("PGVECTOR_DATABASE")
    app_module.connection = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


if __name__ == "__main__":
    configure_runtime()
    app_module.main()
