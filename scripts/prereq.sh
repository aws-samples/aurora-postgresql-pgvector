#!/bin/bash

# Enhanced prereq.sh for Code Editor with PostgreSQL pgvector Workshop
# Optimized for Code Editor environments (Cloud9 support removed)
# Version: 2.0 - Updated November 2025

# Ensure HOME is set
if [ -z "$HOME" ]; then
    export HOME=$(getent passwd $(id -un) | cut -d: -f6)
fi

# Detect environment type
if [ "${CODE_EDITOR_MODE}" == "true" ]; then
    echo "Running in Code Editor mode"
    export ENV_TYPE="code-editor"
else
    echo "Running in standard mode"
    export ENV_TYPE="standard"
fi

# Main repository configuration
export DefaultCodeRepository="${DefaultCodeRepository:-https://github.com/aws-samples/aurora-postgresql-pgvector.git}"
export PROJ_NAME="aurora-postgresql-pgvector"

# Blaize Bazaar configuration (now part of main repo)
export BLAIZE_PROJ_NAME="blaize-bazaar"
export BLAIZE_PATH="/workshop/aurora-postgresql-pgvector/blaize-bazaar"

# Python configuration
export PYTHON_MAJOR_VERSION="3.11"
export PYTHON_MINOR_VERSION="9"
export PYTHON_VERSION="${PYTHON_MAJOR_VERSION}.${PYTHON_MINOR_VERSION}"

# Get AWS region from environment or default to us-west-2
export AWS_REGION=${AWS_REGION:-us-west-2}
echo "Using AWS Region: $AWS_REGION"

# Workshop user (can be overridden by environment)
export WORKSHOP_USER="${WORKSHOP_USER:-$(whoami)}"
echo "Workshop user: $WORKSHOP_USER"

# TERM setting for output redirection
if [ "X${TERM}" == "X" ]; then
    TERM=/dev/null
fi

function check_aws_cli()
{
    if ! command -v aws &> /dev/null; then
        echo "AWS CLI is not installed"
        return 1
    fi
   
    if ! aws sts get-caller-identity &> /dev/null; then
        echo "AWS CLI is not properly configured or doesn't have proper credentials"
        return 1
    fi
   
    return 0
}

function git_clone()
{
    local clone_dir
    
    # Determine clone directory based on environment
    if [ "$ENV_TYPE" == "code-editor" ]; then
        clone_dir="/workshop"
    else
        clone_dir="${HOME}/environment"
    fi
    
    sudo mkdir -p "$clone_dir"
    cd "$clone_dir" || { echo "Failed to change directory to $clone_dir"; return 1; }
    
    # Clone main repository if URL is provided
    if [ -n "$DefaultCodeRepository" ] && [ "$DefaultCodeRepository" != "" ]; then
        if [ -d "$PROJ_NAME" ]; then
            echo "Directory $PROJ_NAME already exists. Removing it before cloning."
            sudo rm -rf "$PROJ_NAME"
        fi
        git clone "$DefaultCodeRepository" || { echo "Failed to clone main repository"; return 1; }
        echo "Successfully cloned main repository to $clone_dir/$PROJ_NAME"
    fi
    
    # Note: Blaize Bazaar is already included in the main repository
    # No need to clone separately
    
    # Set proper ownership
    sudo chown -R $WORKSHOP_USER:$WORKSHOP_USER "$clone_dir" 2>/dev/null || true
}

function create_env_file()
{
    local repo_dir="$BLAIZE_PATH"
    local env_file="${repo_dir}/.env"

    # Only create .env file if Blaize Bazaar directory exists
    if [ ! -d "$repo_dir" ]; then
        echo "Blaize Bazaar directory not found at $repo_dir, skipping .env file creation"
        return 0
    fi

    # Ensure we're in the repository directory
    cd "$repo_dir" || { echo "Failed to change directory to $repo_dir"; return 1; }

    # Create or overwrite the .env file
    cat > "$env_file" << EOL
# Database configuration
# Note: Don't change these values
DB_HOST=${PGHOST}
DB_PORT=5432
DB_NAME=postgres
DB_USER=${PGUSER}
DB_PASSWORD=${PGPASSWORD}

# AWS configuration
# Note: Don't change these values
AWS_REGION=${AWS_REGION}

# Bedrock configuration
# Note: Don't change these values
BEDROCK_CLAUDE_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
BEDROCK_CLAUDE_MODEL_ARN=arn:aws:bedrock:${AWS_REGION}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0

# Lambda configuration
# Note: Don't change this value
LAMBDA_FUNCTION_NAME=genai-dat-301-labs_BedrockAgent_Lambda
EOL

    echo "Created .env file at $env_file"
    sudo chown $WORKSHOP_USER:$WORKSHOP_USER "$env_file"
}

function setup_venv()
{
    local repo_dir="$BLAIZE_PATH"

    # Only setup venv if Blaize Bazaar directory exists
    if [ ! -d "$repo_dir" ]; then
        echo "Blaize Bazaar directory not found at $repo_dir, skipping virtual environment setup"
        return 0
    fi

    cd "$repo_dir" || { echo "Failed to change directory to $repo_dir"; return 1; }

    # Create .env file first
    create_env_file || { echo "Failed to create .env file"; return 1; }

    # Create virtual environment if it doesn't exist
    if [ -d "venv-blaize-bazaar" ]; then
        echo "Virtual environment already exists, skipping creation"
        return 0
    fi

    echo "Creating virtual environment with Python ${PYTHON_MAJOR_VERSION}..."
    
    # Use Python 3.11 explicitly
    PYTHON_CMD="/usr/local/bin/python${PYTHON_MAJOR_VERSION}"
    
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo "Python ${PYTHON_MAJOR_VERSION} not found at $PYTHON_CMD"
        return 1
    fi

    $PYTHON_CMD -m venv "./venv-blaize-bazaar" || { echo "Failed to create virtual environment"; return 1; }

    # Activate virtual environment and install requirements
    source "./venv-blaize-bazaar/bin/activate" || { echo "Failed to activate virtual environment"; return 1; }
    
    echo "Upgrading pip in virtual environment..."
    python -m pip install --upgrade pip > ${TERM} 2>&1

    # Install requirements if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        echo "Installing packages from requirements.txt..."
        python -m pip install -r requirements.txt || { echo "Failed to install requirements"; return 1; }
    fi
    
    # Install additional critical packages
    echo "Installing additional packages (boto3, psycopg2-binary, langchain)..."
    python -m pip install boto3 psycopg2-binary langchain langchain-aws langchain-community > ${TERM} 2>&1
    
    # Verify critical imports
    echo "Verifying package installations..."
    python -c "import boto3; print('✅ boto3 installed')" || echo "❌ boto3 not available"
    python -c "import streamlit; print('✅ streamlit installed')" || echo "❌ streamlit not available"
    python -c "import psycopg2; print('✅ psycopg2 installed')" || echo "❌ psycopg2 not available"
    python -c "import langchain; print('✅ langchain installed')" || echo "❌ langchain not available"
    
    deactivate

    echo "Successfully set up virtual environment with Python ${PYTHON_MAJOR_VERSION}"
    sudo chown -R $WORKSHOP_USER:$WORKSHOP_USER "$repo_dir"
}

function print_line()
{
    echo "---------------------------------"
}

function install_packages()
{
    local current_dir
    current_dir=$(pwd)
    
    sudo yum install -y jq > "${TERM}" 2>&1
    print_line
    
    echo "Installing aws cli v2"
    print_line
    if aws --version 2>/dev/null | grep -q "aws-cli/2"; then
        echo "AWS CLI v2 is already installed"
        print_line
        return
    fi
    
    cd /tmp || { echo "Failed to change directory to /tmp"; return 1; }
    
    # Detect architecture for AWS CLI download
    ARCH=$(uname -m)
    if [ "$ARCH" == "aarch64" ]; then
        AWS_CLI_URL="https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip"
    else
        AWS_CLI_URL="https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip"
    fi
    
    curl "$AWS_CLI_URL" -o "awscliv2.zip" > "${TERM}" 2>&1
    unzip -o awscliv2.zip > "${TERM}" 2>&1
    sudo ./aws/install --update > "${TERM}" 2>&1
    cd "$current_dir" || { echo "Failed to return to original directory"; return 1; }
    
    print_line
}

function install_postgresql()
{
    print_line
    echo "Installing PostgreSQL 16 client"
    print_line

    # Install PostgreSQL 16 for Amazon Linux 2023
    sudo yum install -y postgresql16 postgresql16-devel > ${TERM} 2>&1

    # Verify installation
    if command -v psql > /dev/null; then
        echo "PostgreSQL 16 client installed successfully"
        psql --version
    else
        echo "PostgreSQL installation failed"
        return 1
    fi
}

function configure_pg()
{
    # Ensure AWS CLI is using the instance profile
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN

    # Use already set AWS_REGION or get from metadata
    if [ -z "$AWS_REGION" ]; then
        export AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "us-west-2")
    fi
    echo "Using AWS Region: $AWS_REGION"
    
    # Print current IAM role information
    echo "Current IAM role:"
    aws sts get-caller-identity

    # If DB_SECRET_ARN is provided from CloudFormation, use it directly
    if [ -n "$DB_SECRET_ARN" ] && [ "$DB_SECRET_ARN" != "none" ]; then
        echo "Using DB_SECRET_ARN from environment: $DB_SECRET_ARN"
        SECRET_NAME="$DB_SECRET_ARN"
    else
        # Try to find database cluster dynamically
        echo "Looking for Aurora PostgreSQL clusters..."
        DB_CLUSTER_ID=$(aws rds describe-db-clusters \
            --region $AWS_REGION \
            --query 'DBClusters[?Engine==`aurora-postgresql`].DBClusterIdentifier' \
            --output text | head -1)
        
        if [ -z "$DB_CLUSTER_ID" ]; then
            echo "No Aurora PostgreSQL cluster found. Skipping database configuration."
            return 0
        fi
        
        echo "Found cluster: $DB_CLUSTER_ID"
        
        # Try to find the associated secret
        SECRET_NAME=$(aws secretsmanager list-secrets \
            --region $AWS_REGION \
            --query "SecretList[?contains(Name, '$DB_CLUSTER_ID')].ARN" \
            --output text | head -1)
        
        if [ -z "$SECRET_NAME" ]; then
            echo "No secret found for cluster $DB_CLUSTER_ID"
            return 1
        fi
    fi
    
    echo "Using secret: $SECRET_NAME"
    
    # Get secret value
    SECRET_JSON=$(aws secretsmanager get-secret-value \
        --secret-id "$SECRET_NAME" \
        --region $AWS_REGION \
        --query SecretString \
        --output text)
    
    if [ -z "$SECRET_JSON" ]; then
        echo "Failed to retrieve secret value"
        return 1
    fi
    
    # Parse secret
    export PGUSER=$(echo $SECRET_JSON | jq -r .username)
    export PGPASSWORD=$(echo $SECRET_JSON | jq -r .password)
    PGHOST_FROM_SECRET=$(echo $SECRET_JSON | jq -r .host)
    
    # Use host from secret, or try to get cluster endpoint
    if [ -n "$PGHOST_FROM_SECRET" ] && [ "$PGHOST_FROM_SECRET" != "null" ]; then
        export PGHOST=$PGHOST_FROM_SECRET
        echo "DB Host from secret: $PGHOST"
    elif [ -n "$DB_CLUSTER_ID" ]; then
        export PGHOST=$(aws rds describe-db-clusters \
            --region $AWS_REGION \
            --db-cluster-identifier $DB_CLUSTER_ID \
            --query 'DBClusters[0].Endpoint' \
            --output text)
        echo "DB Host from cluster: $PGHOST"
    else
        echo "Could not determine database host"
        return 1
    fi
    
    if [ -z "$PGHOST" ] || [ "$PGHOST" == "None" ] || [ "$PGHOST" == "null" ]; then
        echo "Failed to get database host"
        return 1
    fi
    
    echo "Successfully retrieved database credentials"
    
    # Set environment variables for the current session
    export PGDATABASE=postgres
    export PGPORT=5432
    export PGVECTOR_DRIVER='psycopg2'
    export PGVECTOR_USER=$PGUSER
    export PGVECTOR_PASSWORD=$PGPASSWORD
    export PGVECTOR_HOST=$PGHOST
    export PGVECTOR_PORT=5432
    export PGVECTOR_DATABASE='postgres'

    # Determine the profile file to use
    if [ "$ENV_TYPE" == "code-editor" ]; then
        PROFILE_FILE="$HOME/.bashrc"
    else
        PROFILE_FILE="$HOME/.bash_profile"
    fi

    # Persist values for future sessions
    echo "export PGUSER='$PGUSER'" >> $PROFILE_FILE
    echo "export PGPASSWORD='$PGPASSWORD'" >> $PROFILE_FILE
    echo "export PGHOST='$PGHOST'" >> $PROFILE_FILE
    echo "export AWS_REGION='$AWS_REGION'" >> $PROFILE_FILE
    echo "export AWSREGION='$AWS_REGION'" >> $PROFILE_FILE
    echo "export PGDATABASE='postgres'" >> $PROFILE_FILE
    echo "export PGPORT=5432" >> $PROFILE_FILE
    echo "export DB_NAME=postgres" >> $PROFILE_FILE
    echo "export PGVECTOR_DRIVER='psycopg2'" >> $PROFILE_FILE
    echo "export PGVECTOR_USER='$PGUSER'" >> $PROFILE_FILE
    echo "export PGVECTOR_PASSWORD='$PGPASSWORD'" >> $PROFILE_FILE
    echo "export PGVECTOR_HOST='$PGHOST'" >> $PROFILE_FILE
    echo "export PGVECTOR_PORT=5432" >> $PROFILE_FILE
    echo "export PGVECTOR_DATABASE='postgres'" >> $PROFILE_FILE

    source $PROFILE_FILE

    echo "Environment variables set and persisted to $PROFILE_FILE"

    # Create .pgpass file for passwordless psql access
    PGPASS_FILE="$HOME/.pgpass"
    echo "$PGHOST:5432:*:$PGUSER:$PGPASSWORD" > $PGPASS_FILE
    chmod 600 $PGPASS_FILE
    echo "Created .pgpass file for passwordless psql access"

    # Test the connection
    if PGPASSWORD=$PGPASSWORD psql -h $PGHOST -U $PGUSER -d postgres -c "SELECT 1" >/dev/null 2>&1; then
        echo "Successfully connected to the database."
    else
        echo "Failed to connect to the database. Please check your credentials and network settings."
        return 1
    fi
}

function install_python3()
{
    print_line
    echo "Installing Python ${PYTHON_VERSION}"
    print_line

    # Check if Python 3.11 is already installed
    echo "Checking if python${PYTHON_MAJOR_VERSION} is already installed"
    if command -v /usr/local/bin/python${PYTHON_MAJOR_VERSION} &> /dev/null; then 
        echo "Python${PYTHON_MAJOR_VERSION} already exists"
        /usr/local/bin/python${PYTHON_MAJOR_VERSION} --version
        return 0
    fi

    # Install build dependencies
    echo "Installing build dependencies..."
    sudo yum groupinstall -y "Development Tools" > ${TERM} 2>&1
    sudo yum install -y \
        gcc \
        openssl-devel \
        bzip2-devel \
        libffi-devel \
        zlib-devel \
        wget \
        make \
        sqlite-devel \
        readline-devel \
        tk-devel \
        gdbm-devel \
        libuuid-devel \
        ncurses-devel \
        xz-devel > ${TERM} 2>&1

    cd /tmp
    
    # Clean up any previous build attempts
    sudo rm -rf Python-${PYTHON_VERSION}*
    
    echo "Downloading Python ${PYTHON_VERSION}"
    wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz > ${TERM} 2>&1 || { echo "Failed to download Python"; return 1; }
    tar xzf Python-${PYTHON_VERSION}.tgz > ${TERM} 2>&1 || { echo "Failed to extract Python"; return 1; }
    cd Python-${PYTHON_VERSION}
    
    echo "Configuring Python (this may take a few minutes)..."
    ./configure --enable-optimizations --prefix=/usr/local --with-ensurepip=install > ${TERM} 2>&1 || { echo "Failed to configure Python"; return 1; }
    
    echo "Building Python (this will take 5-10 minutes)..."
    make -j$(nproc) > ${TERM} 2>&1 || { echo "Failed to build Python"; return 1; }
    
    echo "Installing Python..."
    sudo make altinstall > ${TERM} 2>&1 || { echo "Failed to install Python"; return 1; }
    
    # Clean up
    cd /tmp
    sudo rm -rf Python-${PYTHON_VERSION} Python-${PYTHON_VERSION}.tgz

    echo "Creating Python symlinks..."
    sudo ln -sf /usr/local/bin/python${PYTHON_MAJOR_VERSION} /usr/local/bin/python
    sudo ln -sf /usr/local/bin/pip${PYTHON_MAJOR_VERSION} /usr/local/bin/pip

    echo "Upgrading pip..."
    /usr/local/bin/python${PYTHON_MAJOR_VERSION} -m pip install --upgrade pip > ${TERM} 2>&1

    # Verify installation
    /usr/local/bin/python${PYTHON_MAJOR_VERSION} --version
    echo "Python ${PYTHON_VERSION} installation completed successfully"
}

function activate_venv()
{
    local venv_path="$BLAIZE_PATH/venv-blaize-bazaar/bin/activate"

    if [ -f "$venv_path" ]; then
        echo "Activating virtual environment"
        source "$venv_path" || { echo "Failed to activate virtual environment"; return 1; }
        echo "Virtual environment activated successfully"
    else
        echo "Virtual environment not found at $venv_path (this is normal if Blaize Bazaar is not available)"
        return 0
    fi
}

function set_bedrock_env_vars() {
    echo "Setting Bedrock and S3 environment variables from CloudFormation outputs..."
    
    # Get values directly from CloudFormation outputs without specifying stack name
    export S3_KB_BUCKET=$(aws cloudformation describe-stacks \
        --query "Stacks[].Outputs[?(OutputKey == 'BedrockS3Bucket')][].{OutputValue:OutputValue}" --output text 2>/dev/null || echo "")
    
    export BEDROCK_KB_ID=$(aws cloudformation describe-stacks \
        --query "Stacks[].Outputs[?(OutputKey == 'BedrockKnowledgeBaseId')][].{OutputValue:OutputValue}" --output text 2>/dev/null || echo "")
    
    export BEDROCK_AGENT_ID=$(aws cloudformation describe-stacks \
        --query "Stacks[].Outputs[?(OutputKey == 'BedrockAgentId')][].{OutputValue:OutputValue}" --output text 2>/dev/null || echo "")
    
    # Get full alias ID and extract the actual alias part
    local FULL_ALIAS_ID=$(aws cloudformation describe-stacks \
        --query "Stacks[].Outputs[?(OutputKey == 'BedrockAgentAliasId')][].{OutputValue:OutputValue}" --output text 2>/dev/null || echo "")
    
    if [ -n "$FULL_ALIAS_ID" ]; then
        export BEDROCK_AGENT_ALIAS_ID=$(echo "$FULL_ALIAS_ID" | cut -d'|' -f2)
    fi
    
    # Determine the profile file to use
    if [ "$ENV_TYPE" == "code-editor" ]; then
        PROFILE_FILE="$HOME/.bashrc"
    else
        PROFILE_FILE="$HOME/.bash_profile"
    fi
    
    # Only proceed if we have some Bedrock variables (not all may be available)
    if [ -n "$S3_KB_BUCKET" ] || [ -n "$BEDROCK_KB_ID" ] || [ -n "$BEDROCK_AGENT_ID" ]; then
        # Write variables to profile
        echo "Writing Bedrock variables to $PROFILE_FILE..."
        {
            echo "# Bedrock KB and S3 environment variables"
            [ -n "$S3_KB_BUCKET" ] && echo "export S3_KB_BUCKET='${S3_KB_BUCKET}'"
            [ -n "$BEDROCK_KB_ID" ] && echo "export BEDROCK_KB_ID='${BEDROCK_KB_ID}'"
            [ -n "$BEDROCK_AGENT_ID" ] && echo "export BEDROCK_AGENT_ID='${BEDROCK_AGENT_ID}'"
            [ -n "$BEDROCK_AGENT_ALIAS_ID" ] && echo "export BEDROCK_AGENT_ALIAS_ID='${BEDROCK_AGENT_ALIAS_ID}'"
        } >> $PROFILE_FILE
        
        # Append to the .env file if it exists
        ENV_FILE="$BLAIZE_PATH/.env"
        if [ -f "$ENV_FILE" ]; then
            echo "Appending Bedrock and S3 variables to .env file..."
            {
                echo ""
                echo "# Bedrock and S3 configuration"
                [ -n "$S3_KB_BUCKET" ] && echo "S3_KB_BUCKET=${S3_KB_BUCKET}"
                [ -n "$BEDROCK_KB_ID" ] && echo "BEDROCK_KB_ID=${BEDROCK_KB_ID}"
                [ -n "$BEDROCK_AGENT_ID" ] && echo "BEDROCK_AGENT_ID=${BEDROCK_AGENT_ID}"
                [ -n "$BEDROCK_AGENT_ALIAS_ID" ] && echo "BEDROCK_AGENT_ALIAS_ID=${BEDROCK_AGENT_ALIAS_ID}"
            } >> "$ENV_FILE"
        fi
        
        # Source the updated profile to make variables available immediately
        source $PROFILE_FILE
        
        echo "Bedrock environment variables set successfully"
    else
        echo "No Bedrock CloudFormation outputs found (this is normal for basic setups)"
    fi
}

##############################################
# CODE EDITOR SPECIFIC FUNCTIONS
##############################################

function setup_code_editor_bashrc() {
    if [ "$ENV_TYPE" != "code-editor" ]; then
        return 0
    fi
    
    echo "Configuring bashrc for Code Editor environment..."
    
    # Add workshop-specific configurations
    cat >> $HOME/.bashrc << 'EOF'

# Workshop environment variables
export PATH="/usr/local/bin:$PATH"
export PYTHONPATH="/usr/local/lib/python3.11/site-packages:$PYTHONPATH"

# PostgreSQL connection helpers - simple psql command works now!
alias psql='psql -h $PGHOST -U $PGUSER -d postgres'
alias pgversion='psql -c "SELECT version();"'

# Virtual environment helper
alias activate-blaize='cd /workshop/aurora-postgresql-pgvector/blaize-bazaar && source venv-blaize-bazaar/bin/activate'

# Streamlit runner
alias run-blaize='cd /workshop/aurora-postgresql-pgvector/blaize-bazaar && source venv-blaize-bazaar/bin/activate && streamlit run Home.py --server.port 8501'

# Workshop banner
echo "🚀 Welcome to GenAI pgvector Workshop!"
echo "============================================================"
echo "🔍 Testing Aurora PostgreSQL Connection..."
echo "============================================================"

# Test database connection
if command -v psql &> /dev/null && [ -n "$PGHOST" ]; then
    if python3 -c "import psycopg2" &> /dev/null; then
        if PGPASSWORD=$PGPASSWORD psql -h $PGHOST -U $PGUSER -d postgres -c "SELECT 1" >/dev/null 2>&1; then
            echo "✅ Connected to Aurora PostgreSQL successfully!"
        else
            echo "⚠️  Database credentials configured but connection failed"
        fi
    else
        echo "❌ Missing required Python package: No module named 'psycopg2'"
    fi
else
    echo "⚠️  Database connection not configured"
fi

echo "============================================================"
echo "📚 Quick Start Guide:"
echo "   1. 🔐 Bedrock models are pre-configured"
echo "   2. 📖 Follow the lab instructions"
echo "   3. 🎯 Navigate to aurora-postgresql-pgvector/blaize-bazaar for advanced labs"
echo ""
echo "📊 Database Commands:"
echo "   psql                                   - Connect to Aurora PostgreSQL (passwordless!)"
echo "   python3 /workshop/test_connection.py   - Test database connection"
echo ""
echo "🐍 Python Version: $(python3 --version 2>/dev/null || echo 'Not configured')"
echo ""
echo "🛍️ Blaize Bazaar: Ready for advanced labs"
echo "   cd /workshop/aurora-postgresql-pgvector/blaize-bazaar"
echo "   source venv-blaize-bazaar/bin/activate && streamlit run Home.py --server.port 8501"
echo ""
echo "Happy coding! 🎉"
EOF

    echo "Code Editor bashrc configuration complete"
}

function create_db_test_script() {
    echo "Creating database connection test script..."
    
    cat > /workshop/test_connection.py << 'PYTHON'
#!/usr/bin/env python3
"""
Database Connection Test Script
Tests connection to Aurora PostgreSQL and pgvector extension
"""

import os
import sys

def test_connection():
    try:
        import psycopg2
        print("✅ psycopg2 module loaded successfully")
    except ImportError:
        print("❌ Error: psycopg2 not installed")
        print("   Install with: pip install psycopg2-binary")
        return False
    
    # Get connection parameters from environment
    host = os.environ.get('PGHOST')
    user = os.environ.get('PGUSER')
    password = os.environ.get('PGPASSWORD')
    database = os.environ.get('PGDATABASE', 'postgres')
    
    if not all([host, user, password]):
        print("❌ Error: Database credentials not set in environment")
        print("   Required: PGHOST, PGUSER, PGPASSWORD")
        return False
    
    try:
        print(f"🔌 Connecting to {host}...")
        conn = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=5432
        )
        print("✅ Connected to database successfully!")
        
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"📊 PostgreSQL Version: {version}")
        
        # Test pgvector extension
        try:
            cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            if cursor.fetchone():
                print("✅ pgvector extension is installed")
            else:
                print("⚠️  pgvector extension not found (may need to be enabled)")
        except Exception as e:
            print(f"⚠️  Could not check pgvector extension: {e}")
        
        cursor.close()
        conn.close()
        print("\n✅ Database connection test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
PYTHON

    chmod +x /workshop/test_connection.py
    echo "Database test script created at /workshop/test_connection.py"
}

function create_streamlit_fix() {
    echo "Creating Streamlit fix script..."
    
    cat > /workshop/fix_streamlit.sh << 'BASH'
#!/bin/bash
# Fix for Streamlit in Code Editor environment

cd /workshop/aurora-postgresql-pgvector/blaize-bazaar
source venv-blaize-bazaar/bin/activate

# Reinstall streamlit if needed
pip install --upgrade streamlit

# Create .streamlit config directory
mkdir -p .streamlit

# Create config.toml
cat > .streamlit/config.toml << EOF
[server]
port = 8501
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
EOF

echo "✅ Streamlit configuration updated"
echo "Run with: streamlit run Home.py --server.port 8501"
BASH

    chmod +x /workshop/fix_streamlit.sh
    echo "Streamlit fix script created at /workshop/fix_streamlit.sh"
}

function create_startup_check() {
    echo "Creating startup check script..."
    
    cat > /workshop/startup_check.sh << 'BASH'
#!/bin/bash
# Startup check script for workshop environment

echo "=== Workshop Environment Check ==="
echo ""

# Check Python
echo "Python 3.11:"
/usr/local/bin/python3.11 --version 2>/dev/null && echo "  ✅ Installed" || echo "  ❌ Not found"

# Check PostgreSQL
echo "PostgreSQL:"
psql --version 2>/dev/null && echo "  ✅ Installed" || echo "  ❌ Not found"

# Check AWS CLI
echo "AWS CLI:"
aws --version 2>/dev/null && echo "  ✅ Installed" || echo "  ❌ Not found"

# Check directories
echo "Workshop directories:"
[ -d "/workshop/aurora-postgresql-pgvector" ] && echo "  ✅ Main repo cloned" || echo "  ❌ Main repo missing"
[ -d "/workshop/blaize-bazaar" ] && echo "  ✅ Blaize Bazaar cloned" || echo "  ❌ Blaize Bazaar missing"

# Check virtual environment
echo "Virtual environment:"
[ -d "/workshop/blaize-bazaar/venv-blaize-bazaar" ] && echo "  ✅ Created" || echo "  ❌ Not found"

# Check database connection
echo "Database connection:"
if [ -n "$PGHOST" ]; then
    echo "  ✅ Credentials configured (Host: $PGHOST)"
else
    echo "  ❌ Credentials not configured"
fi

echo ""
echo "=== End of Check ==="
BASH

    chmod +x /workshop/startup_check.sh
    echo "Startup script created and configured"
}

function create_workshop_readme() {
    echo "Creating workshop README..."
    
    cat > /workshop/README.md << 'MARKDOWN'
# GenAI pgvector Workshop Environment

## Quick Start

### Database Connection
```bash
# Connect to PostgreSQL (passwordless - credentials auto-loaded!)
psql

# Or explicitly specify connection details
psql -h $PGHOST -U $PGUSER -d postgres

# Test connection with Python
python3 /workshop/test_connection.py
```

### Blaize Bazaar Application
```bash
# Navigate to Blaize Bazaar
cd /workshop/aurora-postgresql-pgvector/blaize-bazaar

# Activate virtual environment
source venv-blaize-bazaar/bin/activate

# Run Streamlit app
streamlit run Home.py --server.port 8501
```

### Python Environment
- **Global Python**: 3.11.9 at `/usr/local/bin/python3.11`
- **Virtual Environment**: `/workshop/aurora-postgresql-pgvector/blaize-bazaar/venv-blaize-bazaar`
- **Packages**: boto3, psycopg2, streamlit, langchain, and more

### Environment Variables
All necessary environment variables are set in `~/.bashrc`:
- Database: `PGHOST`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- AWS: `AWS_REGION`, `AWS_ACCOUNTID`
- Application: All vars in `/workshop/aurora-postgresql-pgvector/blaize-bazaar/.env`

### Passwordless PostgreSQL Access
A `.pgpass` file has been created in your home directory for passwordless psql access.
Simply type `psql` to connect - no password needed!

### Useful Aliases
- `psql` - Connect to PostgreSQL (passwordless!)
- `pgversion` - Show PostgreSQL version
- `activate-blaize` - Activate Blaize Bazaar venv
- `run-blaize` - Run Streamlit app

## Troubleshooting

### Streamlit Issues
```bash
cd /workshop
./fix_streamlit.sh
```

### Environment Check
```bash
/workshop/startup_check.sh
```

### Database Connection Issues
1. Verify environment variables: `echo $PGHOST`
2. Test connection: `python3 /workshop/test_connection.py`
3. Check security groups and network access
4. Verify .pgpass file: `ls -la ~/.pgpass` (should be 600 permissions)

## Workshop Structure
```
/workshop/
├── aurora-postgresql-pgvector/   # Main workshop repository
│   ├── blaize-bazaar/            # Streamlit application
│   │   ├── venv-blaize-bazaar/  # Python virtual environment
│   │   ├── .env                  # Environment configuration
│   │   └── Home.py               # Main Streamlit app
│   ├── notebooks/                # Jupyter notebooks
│   ├── scripts/                  # Helper scripts
│   └── ...                       # Other workshop materials
├── test_connection.py            # Database test script
├── fix_streamlit.sh             # Streamlit troubleshooting
├── startup_check.sh             # Environment validation
└── README.md                    # This file
```

## Support
For issues, refer to the workshop documentation or contact your instructor.
MARKDOWN

    echo "Workshop README created at /workshop/README.md"
}

function copy_logs_to_s3()
{
    local region=${AWS_REGION:-us-west-2}
    local account_id=${AWS_ACCOUNTID:-$(aws sts get-caller-identity --query Account --output text 2>/dev/null)}
    local current_time=$(date +%s)
    local bucket_name="genai-pgv-labs-${account_id}-${current_time}"
    
    print_line
    
    # Create S3 bucket
    if aws s3 mb s3://${bucket_name} --region ${region} >/dev/null 2>&1; then
        echo ${bucket_name}
        
        # Copy logs if they exist
        if [ -f "/tmp/bootstrap.log" ]; then
            aws s3 cp /tmp/bootstrap.log s3://${bucket_name}/ >/dev/null 2>&1 || \
                echo "Failed to copy logfile to bucket ${bucket_name}"
        else
            echo "The user-provided path /tmp/bootstrap.log does not exist."
            echo "Failed to copy logfile to bucket ${bucket_name}"
        fi
    else
        echo "Failed to create S3 bucket ${bucket_name}"
    fi
}

function run_final_checks()
{
    print_line
    
    # Check AWS Region
    if [ -n "$AWS_REGION" ]; then
        echo "AWS Region set to $AWS_REGION : OK"
    else
        echo "Error: AWS Region not set : NOTOK"
    fi
    
    # Check AWS CLI
    if command -v aws &> /dev/null; then
        echo "AWS CLI configuration : OK"
    else
        echo "Error: AWS CLI not found : NOTOK"
    fi
    
    # Check PostgreSQL
    if command -v psql &> /dev/null; then
        echo "PostgreSQL installation : OK"
        # Test connection
        if [ -n "$PGHOST" ]; then
            if PGPASSWORD=$PGPASSWORD psql -h $PGHOST -U $PGUSER -d postgres -c "SELECT 1" >/dev/null 2>&1; then
                echo "PostgreSQL configuration : OK"
            else
                echo "Error: PostgreSQL connection failed : NOTOK"
            fi
        fi
    else
        echo "PostgreSQL installation : NOTOK"
    fi
    
    # Check main project
    if [ -d "/workshop/$PROJ_NAME" ]; then
        echo "Main project directory : OK"
    else
        echo "Main project directory : NOTOK"
    fi
    
    # Check Blaize Bazaar
    if [ -d "$BLAIZE_PATH" ]; then
        echo "Blaize Bazaar project directory : OK"
    else
        echo "Blaize Bazaar project directory : NOTOK (optional)"
    fi
    
    # Check Python 3.11
    if command -v /usr/local/bin/python3.11 &> /dev/null; then
        echo "Python3.11 installation : OK"
        /usr/local/bin/python3.11 --version
    else
        echo "Error: python3.11 command not found : NOTOK"
    fi
    
    # Check Python symlink
    if command -v python3 &> /dev/null; then
        echo "Python3 symlink : OK"
        python3 --version
    else
        echo "Python3 symlink : NOTOK"
    fi
    
    # Check virtual environment
    if [ -d "$BLAIZE_PATH/venv-blaize-bazaar" ]; then
        echo "Blaize Bazaar virtual environment : OK"
    else
        echo "Blaize Bazaar virtual environment : NOTOK (optional)"
    fi
    
    # Check Bedrock environment variables
    if [ -n "$S3_KB_BUCKET" ] || [ -n "$BEDROCK_KB_ID" ] || [ -n "$BEDROCK_AGENT_ID" ]; then
        echo "Bedrock and S3 environment variables : OK"
    else
        echo "Bedrock and S3 environment variables : Not configured (optional)"
    fi
    
    # Check helper scripts
    if [ -f "/workshop/test_connection.py" ]; then
        echo "Database test script : OK"
    else
        echo "Database test script : NOTOK"
    fi
    
    if [ -f "/workshop/fix_streamlit.sh" ]; then
        echo "Streamlit fix script : OK"
    else
        echo "Streamlit fix script : NOTOK"
    fi
    
    if [ -f "/workshop/startup_check.sh" ]; then
        echo "Startup check script : OK"
    else
        echo "Startup check script : NOTOK"
    fi
    
    # Overall status
    echo "=================================="
    if [ -d "/workshop/$PROJ_NAME" ] && command -v /usr/local/bin/python3.11 &> /dev/null && command -v psql &> /dev/null; then
        echo "✅ Overall status : SUCCESS"
    else
        echo "⚠️  Overall status : FAILED (some optional components may be missing)"
    fi
    echo "=================================="
}

##############################################
# MAIN EXECUTION
##############################################

if [ "X${TERM}" == "X" ]; then
    TERM=/dev/null
fi

echo "=========================================="
echo "GenAI pgvector Workshop Prerequisites"
echo "Environment: $ENV_TYPE"
echo "User: $WORKSHOP_USER"
echo "=========================================="
echo "Process started at `date`"

print_line

# Run prerequisite checks and installations
check_aws_cli || { echo "AWS CLI check failed"; exit 1; }

print_line

install_packages

git_clone

print_line

install_python3

print_line

install_postgresql

configure_pg

print_line

setup_venv

print_line

set_bedrock_env_vars

print_line

if [ "$ENV_TYPE" == "code-editor" ]; then
    echo "Running Code Editor specific setup..."
    setup_code_editor_bashrc
    create_db_test_script
    create_streamlit_fix
    create_startup_check
    create_workshop_readme
fi

print_line

run_final_checks

copy_logs_to_s3

activate_venv

echo "=========================================="
echo "✅ Process completed at `date`"
echo "=========================================="
