import os
import traceback

import boto3
import streamlit as st
from dotenv import load_dotenv

import app as app_module


def configure_runtime():
    load_dotenv()

    aws_region = os.getenv("AWS_REGION", app_module.DEFAULT_REGION)
    app_module.BEDROCK_CLIENT = boto3.client("bedrock-runtime", aws_region)

    db_user = os.getenv("PGUSER") or os.getenv("PGVECTOR_USER")
    db_password = os.getenv("PGPASSWORD") or os.getenv("PGVECTOR_PASSWORD")
    db_host = os.getenv("PGHOST") or os.getenv("PGVECTOR_HOST")
    db_port = os.getenv("PGPORT") or os.getenv("PGVECTOR_PORT") or "5432"
    db_name = os.getenv("PGDATABASE") or os.getenv("PGVECTOR_DATABASE")
    app_module.connection = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


if __name__ == "__main__":
    try:
        configure_runtime()
        app_module.main()
    except Exception as e:
        st.error(f"Application initialization error: {str(e)}")
        print(traceback.format_exc())
