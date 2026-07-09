import os
import sys
import traceback

import boto3
import streamlit as st
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import app as app_module
from rag_shared import build_pg_connection_string


def configure_runtime():
    load_dotenv()

    aws_region = os.getenv("AWS_REGION", app_module.DEFAULT_REGION)
    app_module.BEDROCK_CLIENT = boto3.client("bedrock-runtime", aws_region)
    app_module.connection = build_pg_connection_string()


if __name__ == "__main__":
    try:
        configure_runtime()
        app_module.main()
    except Exception as e:
        st.error(f"Application initialization error: {str(e)}")
        print(traceback.format_exc())
