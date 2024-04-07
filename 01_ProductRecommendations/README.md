# Building AI-powered search in PostgreSQL using Amazon SageMaker and pgvector

This repository guides users through creating a product similarity search using Amazon SageMaker and Amazon Aurora for PostgreSQL using the extension `pgvector`.

# How does it work?

we have used pre-trained model [`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) from Hugging Face SentenceTransformers to generate fixed 384 length sentence embedding from feidegger, a zalandoresearch dataset. Then those feature vectors are stored in [Amazon Aurora for PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraPostgreSQL.html) using extension `pgvector` for product similarity search.

# Solution

![Architecture](static/architecture.png)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
