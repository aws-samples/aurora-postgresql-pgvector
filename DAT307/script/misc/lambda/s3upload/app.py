import json
import logging
import os
import magic
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from langchain_community.document_loaders import S3FileLoader, JSONLoader, CSVLoader, TextLoader, UnstructuredMarkdownLoader
from langchain_community.embeddings import BedrockEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import AzureAIDocumentIntelligenceLoader
from langchain_community.document_loaders import PyPDFLoader

config = Config(read_timeout=1000)

def get_db_credentials(dbsecret):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=dbsecret)
    secret = response.get('SecretString')
    secret = json.loads(secret)
    return secret.get('username'), secret.get('password'), secret.get('database'), secret.get('host'), secret.get('port')

def lambdaHandler(event, context):
    print (event)
    print (context)
    s3_client = boto3.client('s3')
    bucket_name = event.get('Records', [])[0].get('s3', {}).get('bucket', {}).get('name')
    object_key = event.get('Records', [])[0].get('s3', {}).get('object', {}).get('key')
    object_key = object_key.replace('%40', '@').replace('+', ' ')
    userId = object_key.split('/')[0]

    print (bucket_name)
    print (object_key)
    print (userId)
    s3 = boto3.client('s3')
    tempfile = '/tmp/tempfile'
    s3.download_file(bucket_name, object_key, tempfile)
    mime = magic.Magic(mime=True)
    filetype = mime.from_file(tempfile)
    if filetype == 'application/json':
        print ("Initializing JSONLoader")
        loader = JSONLoader(tempfile, ".messages[].content")
    elif filetype == 'application/pdf':
        print ("Initializing PyPDFLoader")
        loader = PyPDFLoader((tempfile))
    elif filetype in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        print ("NOT IMPLEMENTED FEATURE for docx, pptx, xlsx, etc")
        pass
    elif filetype == 'text/plain':
        print ("Initializing TextLoader")
        loader = TextLoader(tempfile)
    elif filetype in ['text/csv', 'application/csv']:
        print ("Initializing CSVLoader")
        loader = CSVLoader(file_path=tempfile)
    elif filetype == 'text/markdown':
        print ("Initializing CSVLoader")
        loader = UnstructuredMarkdownLoader(file_path=tempfile)

    chunks = loader.load_and_split()

    # Generate embeddings using Amazon Bedrock
    BEDROCK_CLIENT = boto3.client(service_name="bedrock-runtime", region_name='us-west-2', config=config) 
    embeddings = BedrockEmbeddings(model_id='amazon.titan-embed-text-v2:0', client=BEDROCK_CLIENT)

    user, password, database, host, port = get_db_credentials(os.environ.get('DBSECRET'))

    conn = PGVector.connection_string_from_db_params(
        driver=os.environ.get("PGVECTOR_DRIVER", "psycopg"),
        database=database,
        user=user,
        password=password,
        host=host,
        port=port
    )
    docmetadata={'userId': userId, 's3Uri': f's3://{bucket_name}/{object_key}'}
    store = PGVector(
        collection_name=object_key,
        connection=conn,
        embeddings=embeddings,
        use_jsonb=True,
        create_extension=True,
        collection_metadata=docmetadata,
    )

    for _doc in chunks:
        _doc.metadata['userId'] = userId
        _doc.metadata['source'] = f's3://{bucket_name}/{object_key}'
    store.add_documents(chunks)
    return {'status': 'Success', 's3Uri': f's3://{bucket_name}/{object_key}'}


