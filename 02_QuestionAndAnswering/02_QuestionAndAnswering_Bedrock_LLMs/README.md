# Generative AI Use Cases with Amazon Aurora PostgreSQL, pgvector and Amazon Bedrock

## Introduction - Build and deploy an AI-powered chatbot application

In this lab, we provide a step-by-step guide with all the building blocks for creating an enterprise ready RAG application such as a question answering chatbot. We use a combination of different AWS services including [Amazon Bedrock](https://aws.amazon.com/bedrock/), an easy way to build and scale generative AI applications with foundation models. We use [Titan Text](https://aws.amazon.com/bedrock/titan/) for text embeddings and [Anthropic's Claude on Amazon Bedrock](https://aws.amazon.com/bedrock/claude/) as our LLM and the pgvector extension on Amazon Aurora PostgreSQL-Compatible Edition as our vector database. We also demonstrate integration with open-source frameworks such as LangChain for interfacing with all the components and Streamlit for building the chatbot frontend.

## Architecture

![Architecture](static/RAG_APG.png)

## How It Works

The application follows these steps to provide responses to your questions:

1. **PDF Loading**: The app reads PDF documents and extracts their text content.

2. **Text Chunking**: The extracted text is divided into smaller chunks that can be processed effectively.

3. **Embedding**: The application utilizes Titan Text from Amazon Bedrock to generate vector representations (embeddings) of the text chunks.

4. **User Question**: The user asks a question in natural language. 

5. **Similarity Matching**: When the user asks a question, the app compares it with the text chunks and identifies the most semantically similar ones.

6. **RAG**: The user question and the context from the vector database is passed to the LLM (Anthropic's Claude on Amazon Bedrock).

7. **Response Generation**: The LLM generates a response based on the relevant content of the PDFs.

## Dependencies and Installation

To build the GenAI Q&A chatbot with pgvector and Amazon Aurora PostgreSQL, please follow these steps:

1. Clone the repository to your local machine.

2. Create a new [virtual environment](https://docs.python.org/3/library/venv.html#module-venv) and activate it.
```
python3.9 -m venv env
source env/bin/activate
```

3. Create a `.env` file in your project directory similar to `env.example` to add your HuggingFace access tokens and Aurora PostgreSQL DB cluster details. Your .env file should like the following:
   
```
PGVECTOR_DRIVER='psycopg2'
PGVECTOR_USER='<<Username>>'
PGVECTOR_PASSWORD='<<Password>>'
PGVECTOR_HOST='<<Aurora DB cluster host>>'
PGVECTOR_PORT=5432
PGVECTOR_DATABASE='<<DBName>>'
```

4. Install the required dependencies by running the following command:
```
pip install -r requirements.txt
```

## Usage

To use the GenAI Q&A with pgvector and Amazon Aurora PostgreSQL App, follow these steps:

1. Ensure that you have installed the required dependencies and have access to Amazon Bedrock models that you wish to use.

2. Ensure that you have added Aurora PostgreSQL DB details to the `.env` file.

3. Ensure you have installed the extension `pgvector` on your Aurora PostgreSQL DB cluster:
   ```
   CREATE EXTENSION vector;
   ```

4. Run the `app.py` file using the Streamlit CLI. Execute the following command:
   ```
   streamlit run app.py
   ```

5. The application will launch in your default web browser, displaying the user interface.

6. Load multiple PDF documents into the app by following the provided instructions.

7. Ask questions in natural language about the loaded PDFs using the search interface.


## Contributing

This repository is intended for educational purposes and does not accept further contributions. Feel free to utilize and enhance the app based on your own requirements.

## License

The GenAI Q&A Chatbot with pgvector and Amazon Aurora PostgreSQL-compatible edition application is released under the [MIT-0 License](https://spdx.org/licenses/MIT-0.html).
