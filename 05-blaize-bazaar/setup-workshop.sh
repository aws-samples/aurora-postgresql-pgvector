#!/bin/bash
echo "Setting up Blaize Bazaar for genai-pgvector-labs workshop..."

# Export workshop-specific configurations
export DB_SECRET_NAME="apgpg-pgvector-secret"
export STACK_NAME="genai-pgvector-labs-ProductSearchStack"
export WORKSHOP_BUCKET=$(aws s3 ls | grep knowledgebase- | awk '{print $3}')

echo "Configuration:"
echo "  Secret: $DB_SECRET_NAME"
echo "  Stack: $STACK_NAME"
echo "  S3 Bucket: $WORKSHOP_BUCKET"

# Install requirements if needed
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
fi

echo "✅ Setup complete! You can now run the notebooks or Streamlit app."
