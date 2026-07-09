"""
Shared utilities for the 03-retrieval-augmented-generation labs.

Imported by each app via:
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from rag_shared import get_pdf_text, get_text_chunks, build_pg_connection_string
"""
import os

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_pdf_text(pdf_docs):
    """Extract and concatenate text from a list of uploaded PDF file objects."""
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def get_text_chunks(text):
    """Split *text* into overlapping chunks suitable for embedding."""
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", " "],
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    return text_splitter.split_text(text)


def build_pg_connection_string():
    """
    Build a psycopg3 (asyncpg-compatible) connection URL from env vars.

    Reads standard libpq names (PGUSER, PGPASSWORD, PGHOST, PGPORT,
    PGDATABASE) with PGVECTOR_* as fallbacks for older workshop copies.
    """
    db_user = os.getenv("PGUSER") or os.getenv("PGVECTOR_USER")
    db_password = os.getenv("PGPASSWORD") or os.getenv("PGVECTOR_PASSWORD")
    db_host = os.getenv("PGHOST") or os.getenv("PGVECTOR_HOST")
    db_port = os.getenv("PGPORT") or os.getenv("PGVECTOR_PORT") or "5432"
    db_name = os.getenv("PGDATABASE") or os.getenv("PGVECTOR_DATABASE")
    return f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
