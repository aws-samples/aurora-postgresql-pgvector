import os
import sys

import boto3
from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import app as app_module
from rag_shared import build_pg_connection_string


def configure_runtime():
    load_dotenv()

    aws_region = os.getenv("AWS_REGION", "us-west-2")
    app_module.BEDROCK_CLIENT = boto3.client("bedrock-runtime", aws_region)
    app_module.embeddings = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        client=app_module.BEDROCK_CLIENT,
    )
    app_module.connection = build_pg_connection_string()


if __name__ == "__main__":
    configure_runtime()
    app_module.main()
