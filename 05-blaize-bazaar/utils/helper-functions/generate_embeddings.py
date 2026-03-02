import boto3
import json
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# Initialize Bedrock client
bedrock = boto3.client('bedrock-runtime')

# Function to get embedding for a single text
def get_embedding(text):
    try:
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": text})
        )
        # Read the StreamingBody object
        response_body = json.loads(response['body'].read())
        embedding = response_body['embedding']
        return embedding
    except Exception as e:
        print(f"Error generating embedding for text: {text[:50]}...")
        print(f"Error message: {str(e)}")
        return None

# Parallel processing approach
def generate_embeddings_parallel(df, max_workers=50):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        embeddings = list(tqdm(executor.map(get_embedding, df['product_description']), total=len(df)))
    df['embedding'] = embeddings
    return df

# Load your data
df = pd.read_csv('datasets/top_bottom_100_products.csv')

# Generate embeddings
df_with_embeddings = generate_embeddings_parallel(df)

# Remove rows where embedding generation failed
df_with_embeddings = df_with_embeddings.dropna(subset=['embedding'])

# Save the results
df_with_embeddings.to_csv('datasets/top_bottom_100_products_embeddings.csv', index=False)

print(f"Processed {len(df_with_embeddings)} products. Results saved to 'top_bottom_100_products_embeddings.csv'.")