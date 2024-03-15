# A generative AI-powered chatbot using Amazon Aurora Machine Learning extension and Amazon Bedrock

## Introduction - pgvector and Aurora Machine Learning for Chatbot

[Amazon Aurora Machine Learning](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-ml.html) (Aurora ML) enables builders to create ML-based applications using familiar SQL programming. With recent support for Amazon Bedrock, Aurora ML provides access to foundational models for creating embeddings and generating text for generative AI applications directly in SQL. Now builders can create input text embeddings, perform similarity search on pgvector, and generate text within the same Aurora SQL function. This reduces latency for text generation since document embeddings are in the same table as the text, eliminating the need to return search data to applications. In this example, we demonstrate building an AI-powered chatbot with Aurora ML and Amazon Bedrock.


## Architecture

![Architecture](static/architecture.png)

## Dependencies and Installation

Please follow these steps:

1. Clone the repository to your local machine.

2. Create S3 bucket and Setup Aurora PostgreSQL 15.5.

3. Create a new [virtual environment](https://docs.python.org/3/library/venv.html#module-venv) and launch it.

```
python3.9 -m venv env
source env/bin/activate
```

4. Create a `.env` file in your project directory similar to `env.example` to add your S3 bucket and Aurora PostgreSQL DB details. Your .env file should look like the following:

```
POSTGRESQL_ENDPOINT="auroraml-bedrock-1.cluster-XXXXXX.us-east-1.rds.amazonaws.com"
POSTGRESQL_PORT="5432"
POSTGRESQL_USER="<username>"
POSTGRESQL_PW="<password>"
POSTGRESQL_DBNAME="<dbname>"
REGION=<aws-region-id>
SOURCE_S3_BUCKET="<knowledge-dataset-bucket-name>"
```

5. Install the required dependencies by running the following command:

```
pip install -r requirements.txt
```

6. Make sure you have Cloud9 environment and then make sure you have necessary permissions to call Aurora PostgreSQL from Cloud9 environment. 

## Usage

Please follow these steps:

1. Upload your knowledge dataset to the S3 bucket

2. Configure Aurora PostgreSQL pgvector and aws_ml extensions, and a database table

`python chatbot.py --configure`

2. Ingest your knowledge dataset into Aurora Postgre

`python chatbot.py --ingest`

3. Run chatbot. Use one of the following option to run chatbot.

**Command line mode**
<!-- -->
`python chatbot.py`

**PSQL client**
<!-- -->
Connect to Aurora PostgreSQL using psql client and execute the below command to ask a question and receive a response

`postgres=> SELECT generate_text( 'What was the AWS run rate in year 2022?')`
![Architecture](static/postgres_cli.png)
<!-- -->
**UI mode**
<!-- -->
`streamlit run chatbot-app.py --server.port 8080`

4. Cleanup your resources

<!-- -->
`python chatbot.py --cleanup`
