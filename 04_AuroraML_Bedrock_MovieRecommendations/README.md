# 🎬 Intelligent Movie Recommendations System

This enterprise-ready recommendation system combines Amazon Aurora PostgreSQL with powerful AWS AI services to deliver personalized movie suggestions. Our solution leverages Amazon Bedrock's Titan Text for embeddings and Anthropic's Claude for natural language processing, while using Aurora ML to generate embeddings directly within the database context.

## 🎯 Key Components

We integrate several AWS services to create an efficient recommendation engine:

- **Amazon Bedrock**: Powers our AI capabilities through foundation models
- **Aurora PostgreSQL + pgvector**: Stores and processes vector embeddings
- **Aurora ML**: Generates embeddings directly in the database using Bedrock
- **Titan Text**: Creates text embeddings for movie content
- **Claude**: Provides natural language understanding capabilities

## 🏗️ Architecture

![Architecture](static/ARCH.png)

## 🔄 System Workflow

Our system processes and recommends movies through these key steps:

1. **Data Initialization**: Uses TMDB API data to populate movie details, cast information, and reviews in the PostgreSQL database.

2. **Embedding Generation**: Creates vector representations of movies using `aws_bedrock.invoke_model_get_embeddings`, storing them in vector columns for efficient similarity search.

3. **Recommendation Engine**: Provides suggestions based on:
   - Movie content similarity (cast, genre, overview)
   - Collaborative filtering from user watch patterns

4. **Review Analysis**: Generates concise summaries of movie reviews using `aws_bedrock.invoke_model`.

## 🚀 Setup Guide

### Prerequisites
- AWS account with Bedrock access
- Aurora PostgreSQL cluster
- Completed [Aurora ML setup](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/postgresql-ml.html#postgresql-ml-setting-up-apg-br)

### Installation Steps

1. Clone and setup environment:
```bash
git clone [repository-url]
python3.9 -m venv env
source env/bin/activate
```

2. Configure `.env` file:
```bash
DBDRIVER='psycopg2'
DBUSER='username'
DBPASSWORD='password'
DBHOST='aurora-cluster-host'
DBPORT=5432
DBNAME='dbname'
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Database Setup

1. Enable required extensions:
```sql
CREATE EXTENSION vector;
CREATE EXTENSION aws_ml CASCADE;
```

2. Initialize database:
```sql
CREATE DATABASE moviedb;
\c moviedb
\i data/movies.sql

ALTER TABLE movie.movies ADD COLUMN movie_embedding vector(1536);
```

3. Generate embeddings:
```sql
-- See detailed SQL in Usage section for embedding generation
```

## 💻 Running the Application

1. Launch the application:
```bash
streamlit run ./app.py --server.port 8080
```

2. Access the interface and start exploring movie recommendations.

![Streamlit Application](static/Preview_App.png)

## 🔍 Understanding Vector Embeddings

Our system creates 1536-dimensional vectors that capture movie characteristics including:
- Plot elements and themes
- Genre combinations
- Cast relationships
- User viewing patterns

These embeddings enable the system to understand complex relationships between movies and provide nuanced recommendations.

## 📚 Best Practices

For optimal performance:
- Regularly update movie data and embeddings
- Monitor embedding generation performance
- Index vector columns for faster similarity search
- Implement batch processing for large updates

## 📜 License

Released under the [MIT-0 License](https://spdx.org/licenses/MIT-0.html).

---

*Built with AWS services for intelligent movie recommendations*
