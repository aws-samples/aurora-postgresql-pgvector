import os
import re
import json
import boto3
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import time
import logging
import psycopg2
import psycopg2.extras
import argparse

logger = logging.getLogger("chatbot")
logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s : %(message)s', level=logging.INFO)
logging.getLogger("botocore.credentials").disabled = True

# Model configurations
BEDROCK_MODEL_ID="anthropic.claude-instant-v1"
EMBEDDING_MODEL_ID="amazon.titan-embed-g1-text-02"

# Environment configurations
POSTGRESQL_ENDPOINT=None
POSTGRESQL_PORT=None
POSTGRESQL_USER=None
POSTGRESQL_PW=None
POSTGRESQL_DBNAME=None
REGION = 'us-east-1'
SOURCE_S3_BUCKET=None
try:
    POSTGRESQL_ENDPOINT = os.environ['POSTGRESQL_ENDPOINT']
    POSTGRESQL_PORT = os.environ['POSTGRESQL_PORT']
    POSTGRESQL_USER = os.environ['POSTGRESQL_USER']
    POSTGRESQL_PW = os.environ['POSTGRESQL_PW']
    POSTGRESQL_DBNAME = os.environ['POSTGRESQL_DBNAME']
    REGION = os.environ['REGION']
    SOURCE_S3_BUCKET = os.environ['SOURCE_S3_BUCKET']
    
    error_string ='You must configure {0} in your environment.'
    if len(POSTGRESQL_ENDPOINT) == 0:
        logger.error(error_string.format("POSTGRESQL_ENDPOINT"))
        exit(1)
    if len(POSTGRESQL_PORT) == 0:
        logger.error(error_string.format("POSTGRESQL_PORT"))
        exit(1)
    if len(POSTGRESQL_USER) == 0:
        logger.error(error_string.format("POSTGRESQL_USER"))
        exit(1)
    if len(POSTGRESQL_PW) == 0:
        logger.error(error_string.format("POSTGRESQL_PW"))
        exit(1)
    if len(POSTGRESQL_DBNAME) == 0:
        logger.error(error_string.format("POSTGRESQL_DBNAME"))
        exit(1)
    if len(REGION) == 0:
        logger.error(error_string.format("REGION"))
        exit(1)
    if len(SOURCE_S3_BUCKET) == 0:
        logger.error(error_string.format("SOURCE_S3_BUCKET"))
        exit(1)
        
except KeyError as error:
    logger.error("One or more environment variables are not configured.", error)
    exit(1)

# This function is responsible for getting a database connection.
def get_database_connection():
    session = boto3.Session()
    client = session.client('rds')
    
    try:
        conn = psycopg2.connect(host=POSTGRESQL_ENDPOINT, 
            port=POSTGRESQL_PORT, 
            database=POSTGRESQL_DBNAME, 
            user=POSTGRESQL_USER, 
            password=POSTGRESQL_PW, 
            sslrootcert="SSLCERTIFICATE")
        return conn
    except Exception as e:
        logger.error("Database connection failed due to {}".format(e))   
    return None

def get_generate_embedding_func_sql():
    sql_string = """ 
    CREATE OR REPLACE PROCEDURE generate_embeddings()
    AS $emb$
        DECLARE
            doc RECORD;
            emb vector(1536);
            titan_model_input text;
        BEGIN
            -- create embeddings for content column and save them in embedding column
            FOR doc in SELECT id, content FROM auroraml_chatbot
            LOOP
               SELECT format('{{ "inputText": "%s"}}', doc.content) INTO titan_model_input;
               SELECT * from aws_bedrock.invoke_model_get_embeddings(
                  model_id      := '{0}',
                  content_type  := 'application/json',
                  json_key      := 'embedding',
                  model_input   := titan_model_input)
               INTO emb;
               
               UPDATE auroraml_chatbot SET embedding = emb WHERE id = doc.id;
            END LOOP;
        END;
    $emb$ 
    LANGUAGE plpgsql;    
    """
    return sql_string.format(EMBEDDING_MODEL_ID)

def get_generate_text_func_sql():
    sql_string = """ 
    CREATE OR REPLACE FUNCTION generate_text ( question text )
    RETURNS text AS $emb$
    DECLARE
       titan_model_input text;
       claude_model_input text;
       question_v vector(1536);
       context text;
       prompt text;
       response text;
    BEGIN
    
        SELECT format('{{ "inputText": "%s"}}', question) INTO titan_model_input;
        SELECT * from aws_bedrock.invoke_model_get_embeddings(
            model_id      := '{0}',
            content_type  := 'application/json',
            json_key      := 'embedding',
            model_input   := titan_model_input)
        INTO question_v;
    
        SELECT content, 1 - (embedding <=> question_v) AS cosine_similarity INTO context FROM auroraml_chatbot ORDER by 2 DESC;
    
        SELECT format('\\n\\nHuman: You are a helpful assistant that answers questions directly and only using the information provided in the context below.\\nDescribe the answer in detail.\\n\\nContext: %s \\n\\nQuestion: %s \\n\\nAssistant:', context, question) INTO prompt;
       
        SELECT format('{{"prompt":"%s","max_tokens_to_sample":4096,"temperature":0.5,"top_k":250,"top_p":0.5,"stop_sequences":[]}}', prompt) INTO claude_model_input;
    
        SELECT * FROM aws_bedrock.invoke_model (
            model_id    := '{1}',
            content_type:= 'application/json',
            accept_type := 'application/json',
            model_input := claude_model_input)
        INTO response;
    
        RETURN response;
       
    END;
    $emb$ 
    LANGUAGE plpgsql;
    """
    return sql_string.format(EMBEDDING_MODEL_ID, BEDROCK_MODEL_ID)
    
# This function configures database including pgvector and aws_ml extensions, a database
# table, generate embedding stored procedure, and generate text postgresql function.
def configure_database():
    logger.info("Configuring aurora postgreSQL database...")

    try:
        conn = get_database_connection()
        with conn.cursor() as cur:
            cur.execute("""CREATE EXTENSION IF NOT EXISTS aws_ml CASCADE;""")
            cur.execute("""CREATE EXTENSION IF NOT EXISTS vector;""")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auroraml_chatbot (
                    id int GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    content text NOT NULL,
                    embedding vector(1536)
                );
                """    
            )
            cur.execute(get_generate_embedding_func_sql())
            cur.execute(get_generate_text_func_sql())
            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error) 
        exit(1)
    finally:
        logger.debug("Aurora PostgreSQL was confgured successfully")

# This function removes a database table, generate embeddings SP, generate text function
# , aws_ml and pgvector extensions.
def cleanup_database():
    logger.info("Cleaning up the database...")
    try:
        conn = get_database_connection()
        with conn.cursor() as cur:
            cur.execute("""DROP TABLE IF EXISTS auroraml_chatbot;""")
            cur.execute("""DROP PROCEDURE  IF EXISTS generate_embeddings;""")
            cur.execute("""DROP FUNCTION  IF EXISTS generate_text;""")
            cur.execute("""DROP EXTENSION  IF EXISTS aws_ml CASCADE;""")
            cur.execute("""DROP EXTENSION  IF EXISTS vector;""")
            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)    
        exit(1)
    finally:
        logger.debug("Aurora PostgreSQL was cleaned successfully")

# This function generates embeddings using PostgreSQL generating_embeddings procedure.
def generate_embeddings():
    logger.info("Generating embeddings in database...")
    
    try:
        conn = get_database_connection()
        with conn.cursor() as cur:
            cur.execute('CALL generate_embeddings();')
            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)    
        exit(1)
    finally:
        logger.debug("Embeddings generated successfully!")
        return None

# This function generates text for 'input text' using PostgreSQL generate_text function.
def generate_text(input_text):
    completion = None
    
    try:
        conn = get_database_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT generate_text(%s)", (input_text,))
            row = cur.fetchmany(1)
            if row:
                response_body = row[0][0]
                response_json = json.loads(response_body)
                completion = response_json["completion"]
                
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)   
    finally:
        logger.debug("Invoke aurora executed successfully")
        return completion

# This function inserts a chuck into database table.
def insert_chunk_into_database(content):
    id = None
    try:
        conn = get_database_connection()
        with conn.cursor() as cur:
            cur.execute(""" INSERT INTO auroraml_chatbot(content) 
                            VALUES(%s) RETURNING id;""", (content,))
            rows = cur.fetchall()
            if rows:
                id = rows[0]
            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)    
        exit(1)
    finally:
        logger.debug("Data chunk inserted successfully, id="+str(id))
        return id

# The function escapes any special characters in the data to properly clean it
# before loading into the Aurora PostgreSQL table, which is a best practice 
# since SQL functions can struggle with certain special characters.
# 
# Your documents may have specicial characters that need to be escaped such as
# postgres non-breaking chars etc, you must replace them before ingesting
# into postgres
def clean_chunk(chunk):
    # replace crlf, double quotes, single quote etc.
    data = chunk
    data = re.sub("\n\r", "\\\\n\\\\r", data)
    data = re.sub("\n", "\\\\n", data)
    data = re.sub('"', '\\"', data)
    data = re.sub("\xa0", " ", data)

    return data

# This function inserts the clean chunk into database.
def insert_chunks(chunks):
    logger.debug(f"Ingesting chunk into database, chunks={len(chunks)}")
    for chunk in chunks:
        logger.debug("Raw chunk data::\n"+str(chunk))
        cleaned_data = clean_chunk(str(chunk))
        logger.debug("Prepared chunk data::\n"+cleaned_data)
        insert_chunk_into_database(cleaned_data)

# This function ingests the Amazon S3 dataset into database.
def ingest_knowledge_dataset(bucket_name):
    # load documents from Amazon S3, chunk and load them into aurora postgreSQL table 
    s3_client = boto3.client(service_name="s3",region_name=REGION,)
    objects = s3_client.list_objects_v2(Bucket=bucket_name)
    
    for obj in objects['Contents']:
        s3_filename = obj['Key']
        logger.debug("Downloading file: "+s3_filename)
        
        with open(s3_filename, 'wb') as f:
            s3_client.download_fileobj(bucket_name, s3_filename, f)
        
        logger.debug("Embedding file: "+s3_filename)

        loader = PyPDFLoader(s3_filename)
        docs = loader.load()

        # remove downloaded file
        os.remove(s3_filename)
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 5000,
            chunk_overlap  = 500,
        )
        
        chunks = text_splitter.split_documents(docs)
        insert_chunks(chunks)

# This function ingests the Amazon S3 dataset into database and generate embeddings.
def ingest_and_embed():
    # ingest your documents and generate embeddings
    logger.info("Loading your documents...")
    ingest_knowledge_dataset(SOURCE_S3_BUCKET)
    generate_embeddings()

# This function provides a commandline interface to run chatbot.
def run_cli_mode():
    input_text = ""
    print('To exit, enter "cntl+c" anytime!')
    while input_text != "quit" or input_text != "q":
        input_text=input("\nEnter your question: ")
        ask_question(input_text)

def ask_question(input_text):
    logger.info("Question: "+input_text)

    start_time = time.time()
    response = generate_text(input_text)
    end_time = time.time()
    
    logger.info("Answer:\n"+str(response))
    logger.info("\nResponse Time = "+str(end_time - start_time))
    return response

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--ingest', action='store_true', 
        help='Ingest knowledge dataset into database')
    parser.add_argument('--configure', action='store_true', help='Configure database')
    parser.add_argument('--cleanup', action='store_true', help='Clean database')
    
    args = parser.parse_args()
    if args.ingest:
        ingest_and_embed()
    elif args.configure:
        configure_database()
    elif args.cleanup:
        cleanup_database()
    else:
        run_cli_mode()
    
    
