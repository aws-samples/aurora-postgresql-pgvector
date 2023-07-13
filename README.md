## Leveraging pgvector and Amazon Aurora PostgreSQL for Natural Language Processing, Chatbots and Sentiment Analysis

This repository is associated with the AWS blog post: Leveraging pgvector and Amazon Aurora PostgreSQL for Natural Language Processing, Chatbots and Sentiment Analysis.

## What is pgvector?

pgvector is an open-source extension designed to augment PostgreSQL databases with the capability to store and conduct searches on ML-generated embeddings to identify both exact and approximate nearest neighbors. It’s designed to work seamlessly with other PostgreSQL features, including indexing and querying.

Please review the pgvector [documentation](https://github.com/pgvector/pgvector) for additional details.

To generate vector embeddings, you can use popular open-source frameworks such as LangChain and HuggingFace. [Hugging Face Hub](https://huggingface.co/docs/hub/index) is a platform with over 120k models, 20k datasets, and 50k demo apps, all open source and publicly available, in an online platform where people can easily collaborate and build ML together.

For this blog post, we explore two use cases in the context of pgvector and [Amazon Aurora PostgreSQL-Compatible Edition](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraPostgreSQL.html):

1. First, we build an AI-powered application that lets you ask questions based on content in your PDF files in natural language. We upload PDF files to the application and then type in questions in simple English. Our AI-powered application will process questions and return answers based on the content of the PDF files.

2. Next, we make use of the native integration between pgvector and Amazon Aurora Machine Learning. Machine learning integration with Aurora currently supports Amazon Comprehend and Amazon SageMaker. Aurora makes direct and secure calls to SageMaker and Comprehend that don’t go through the application layer. Aurora machine learning is based on the familiar SQL programming language, so you don’t need to build custom integrations, move data around or learn separate tools.

## Contributing

This repository is intended for educational purposes and does not accept further contributions. Feel free to utilize and enhance the app based on your own requirements.

## License

The The GenAI Q&A Chatbot with pgvector and Amazon Aurora PostgreSQL-compatible edition application is released under the [MIT-0 License](https://spdx.org/licenses/MIT-0.html).
