# Building a Product Recommendations Application using pgvector, Aurora PostgreSQL, Amazon SageMaker and Amazon Bedrock

This repository contains sample code to create a product similarity search solution using Amazon SageMaker, Amazon Bedrock and Aurora PostgreSQL using the `pgvector` extension.

## How It Works

1. `genai-pgvector-similarity-search.ipynb`: We have used the pre-trained model [`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) from Hugging Face SentenceTransformers to generate 384 dimensional text embeddings using the [Zalando Research dataset](https://github.com/zalandoresearch/feidegger) that consists of 8,732 high-resolution images. We then store those vector embeddings in Aurora PostgreSQL for product similarity search.
2. `bedrock-text-search.ipynb`: We have used Amazon Titan Text or [`amazon.titan-embed-g1-text-02`](https://aws.amazon.com/bedrock/titan/) from Amazon Bedrock to generate 1536 dimensional text embeddings using a publicly available [dataset](https://www.kaggle.com/datasets/promptcloud/amazon-product-dataset-2020) that consists of 9000+ products from the Amazon product catalog.

## Architecture

![Architecture](static/architecture.png)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
