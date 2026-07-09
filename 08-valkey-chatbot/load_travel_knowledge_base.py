import argparse
import ast
import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def to_pgvector(value):
    embedding = ast.literal_eval(value)
    return "[" + ",".join(str(item) for item in embedding) + "]"


def load_rows(csv_path):
    with csv_path.open(newline="") as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            if len(row) != 4:
                raise ValueError(f"Expected 4 columns in {csv_path}, found {len(row)}")
            yield int(row[0]), row[1], to_pgvector(row[2]), row[3]


def main():
    parser = argparse.ArgumentParser(description="Load the AZFlights travel knowledge base into Aurora PostgreSQL.")
    parser.add_argument(
        "--csv",
        default="travel_knowledge_base.csv",
        help="Path to the CSV file with id, content, embedding, and category columns.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete existing rows before loading the CSV.",
    )
    args = parser.parse_args()

    load_dotenv()
    csv_path = Path(args.csv)

    conninfo = {
        "host": os.environ["DB_HOST"],
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
    }

    with psycopg.connect(**conninfo) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS travel_knowledge_base (
                    id integer PRIMARY KEY,
                    content text NOT NULL,
                    embedding vector(1024) NOT NULL,
                    category text
                );
                """
            )
            if args.truncate:
                cur.execute("TRUNCATE TABLE travel_knowledge_base;")

            cur.executemany(
                """
                INSERT INTO travel_knowledge_base (id, content, embedding, category)
                VALUES (%s, %s, %s::vector, %s)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    category = EXCLUDED.category;
                """,
                list(load_rows(csv_path)),
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS travel_kb_embedding_hnsw_idx
                ON travel_knowledge_base USING hnsw (embedding vector_cosine_ops);
                """
            )
        conn.commit()


if __name__ == "__main__":
    main()
