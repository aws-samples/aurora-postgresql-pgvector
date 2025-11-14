#!/bin/bash

# Enhanced prereq.sh with Code Editor support
# This script works for both Cloud9 and Code Editor environments

# Ensure HOME is set
if [ -z "$HOME" ]; then
    export HOME=$(getent passwd $(id -un) | cut -d: -f6)
fi

# Detect environment type
if [ "${CODE_EDITOR_MODE}" == "true" ]; then
    echo "Running in Code Editor mode"
    export ENV_TYPE="code-editor"
else
    echo "Running in Cloud9/standard mode"
    export ENV_TYPE="cloud9"
fi

# Main repository configuration
export DefaultCodeRepository="${DefaultCodeRepository:-https://github.com/aws-samples/aurora-postgresql-pgvector.git}"
export PROJ_NAME="aurora-postgresql-pgvector"

# Blaize Bazaar configuration
export BLAIZE_PROJ_NAME="blaize-bazaar"
export BLAIZE_REPO="https://github.com/aws-samples/DAT301-reinvent-2024.git"

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
    
    # Clone Blaize Bazaar repository to /workshop
    local workshop_dir="/workshop"
    sudo mkdir -p "$workshop_dir"
    cd "$workshop_dir" || { echo "Failed to change directory to $workshop_dir"; return 1; }
    
    if [ -d "$BLAIZE_PROJ_NAME" ]; then
        echo "Directory $BLAIZE_PROJ_NAME already exists. Removing it before cloning."
        sudo rm -rf "$BLAIZE_PROJ_NAME"
    fi
    
    # Clone DAT301 repo and extract blaize-bazaar directory
    git clone "$BLAIZE_REPO" temp-dat301 || { echo "Failed to clone DAT301 repository"; return 1; }
    
    if [ -d "temp-dat301/$BLAIZE_PROJ_NAME" ]; then
        sudo mv "temp-dat301/$BLAIZE_PROJ_NAME" "$BLAIZE_PROJ_NAME"
        sudo rm -rf temp-dat301
        echo "Successfully extracted Blaize Bazaar application"
    else
        echo "Warning: Blaize Bazaar directory not found in DAT301 repo"
        sudo rm -rf temp-dat301
    fi
    
    # Set proper ownership
    sudo chown -R $WORKSHOP_USER:$WORKSHOP_USER "$workshop_dir" 2>/dev/null || true
    if [ "$ENV_TYPE" != "code-editor" ]; then
        sudo chown -R $WORKSHOP_USER:$WORKSHOP_USER "$clone_dir" 2>/dev/null || true
    fi
}

function create_env_file() 
{
    local repo_dir="/workshop/${BLAIZE_PROJ_NAME}"
    local env_file="${repo_dir}/.env"
    
    # Only create .env file if Blaize Bazaar directory exists
    if [ ! -d "$repo_dir" ]; then
        echo "Blaize Bazaar directory not found, skipping .env file creation"
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
    local repo_dir="/workshop/${BLAIZE_PROJ_NAME}"
    
    # Only setup venv if Blaize Bazaar directory exists
    if [ ! -d "$repo_dir" ]; then
        echo "Blaize Bazaar directory not found, skipping virtual environment setup"
        return 0
    fi
    
    cd "$repo_dir" || { echo "Failed to change directory to $repo_dir"; return 1; }

    # Create .env file
    create_env_file || { echo "Failed to create .env file"; return 1; }

    # Create virtual environment if it doesn't exist
    if [ -d "venv-blaize-bazaar" ]; then
        echo "Virtual environment already exists, skipping creation"
        return 0
    fi

    echo "Creating virtual environment..."
    # Try different Python versions
    PYTHON_CMD=""
    for py_cmd in python3.11 python3.9 python3; do
        if command -v $py_cmd &> /dev/null; then
            echo "Using $py_cmd for virtual environment"
            PYTHON_CMD=$py_cmd
            break
        fi
    done
    
    if [ -z "$PYTHON_CMD" ]; then
        echo "No suitable Python version found"
        return 1
    fi
    
    $PYTHON_CMD -m venv "./venv-blaize-bazaar" || { echo "Failed to create virtual environment"; return 1; }

    # Activate virtual environment and install requirements
    source "./venv-blaize-bazaar/bin/activate" || { echo "Failed to activate virtual environment"; return 1; }
    python -m pip install --upgrade pip > ${TERM} 2>&1
    
    # Install requirements if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        echo "Installing from requirements.txt..."
        python -m pip install -r requirements.txt || { echo "Failed to install requirements"; return 1; }
    else
        # Install comprehensive packages for all workshop modules
        echo "Installing comprehensive packages for workshop..."
        WORKSHOP_PACKAGES="streamlit plotly altair pandas psycopg2-binary boto3 pgvector numpy requests jupyter ipykernel notebook transformers seaborn matplotlib-inline ipywidgets"
        python -m pip install $WORKSHOP_PACKAGES > ${TERM} 2>&1 || {
            echo "Failed to install some packages, trying individually..."
            # Core packages (critical)
            python -m pip install boto3 || echo "boto3 install failed"
            python -m pip install psycopg2-binary || echo "psycopg2 install failed"
            python -m pip install pgvector || echo "pgvector install failed"
            python -m pip install pandas || echo "pandas install failed"
            python -m pip install numpy || echo "numpy install failed"
            python -m pip install requests || echo "requests install failed"
            # Visualization packages
            python -m pip install streamlit || echo "Streamlit install failed"
            python -m pip install plotly || echo "Plotly install failed"
            python -m pip install altair || echo "altair install failed"
            python -m pip install seaborn || echo "seaborn install failed"
            # Jupyter packages
            python -m pip install jupyter || echo "jupyter install failed"
            python -m pip install ipykernel || echo "ipykernel install failed"
            python -m pip install notebook || echo "notebook install failed"
            # ML packages
            python -m pip install transformers || echo "transformers install failed"
        }
    fi
    
    # Verify and ensure streamlit installation
    echo "Verifying Streamlit installation..."
    if ! python -c "import streamlit" 2>/dev/null; then
        echo "❌ Streamlit not found, installing with retry logic..."
        for i in {1..3}; do
            echo "Streamlit install attempt $i/3"
            if python -m pip install --force-reinstall streamlit plotly altair; then
                if python -c "import streamlit" 2>/dev/null; then
                    echo "✅ Streamlit successfully installed and verified"
                    break
                else
                    echo "❌ Streamlit installed but import failed, retrying..."
                fi
            else
                echo "❌ Streamlit installation failed, attempt $i"
            fi
            sleep 2
        done
        
        # Final verification
        if python -c "import streamlit" 2>/dev/null; then
            echo "✅ Final verification: Streamlit is working"
        else
            echo "⚠️ WARNING: Streamlit installation failed after all attempts"
            echo "Users will need to run: python -m pip install streamlit"
        fi
    else
        echo "✅ Streamlit already installed and working"
    fi
    
    deactivate

    echo "Successfully set up virtual environment and installed requirements"
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
    
    sudo yum install -y jq  > "${TERM}" 2>&1
    print_line
    
    # Cloud9 resize (only if available)
    if command -v curl &> /dev/null; then
        source <(curl -s https://raw.githubusercontent.com/aws-samples/aws-swb-cloud9-init/mainline/cloud9-resize.sh) 2>/dev/null || true
    fi
    
    echo "Installing aws cli v2"
    print_line
    if aws --version | grep -q "aws-cli/2"; then
        echo "AWS CLI v2 is already installed"
        return
    fi
    
    cd /tmp || { echo "Failed to change directory to /tmp"; return 1; }
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" > "${TERM}" 2>&1
    unzip -o awscliv2.zip > "${TERM}" 2>&1
    sudo ./aws/install --update > "${TERM}" 2>&1
    cd "$current_dir" || { echo "Failed to return to original directory"; return 1; }
}

function install_postgresql()
{
    print_line
    echo "Installing PostgreSQL client"
    print_line

    # Update package lists
    sudo yum update -y > ${TERM} 2>&1

    # Try PostgreSQL 14 first, then fallback
    if sudo amazon-linux-extras enable postgresql14 > ${TERM} 2>&1; then
        sudo yum install -y postgresql-server postgresql-contrib sysbench > ${TERM} 2>&1
    else
        # Fallback for different environments
        sudo yum install -y postgresql postgresql-contrib > ${TERM} 2>&1
    fi

    # Verify installation
    if command -v psql > /dev/null; then
        echo "PostgreSQL client installed successfully"
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
        
        echo "Found DB cluster: $DB_CLUSTER_ID"
        
        # Try to find the secret dynamically
        echo "Looking for database secrets..."
        SECRET_NAME=$(aws secretsmanager list-secrets \
            --region $AWS_REGION \
            --query 'SecretList[?contains(Name, `db`) || contains(Name, `postgres`) || contains(Name, `aurora`)].Name' \
            --output text | head -1)
        
        if [ -z "$SECRET_NAME" ]; then
            echo "No database secret found. Skipping database configuration."
            return 0
        fi
    fi
    
    echo "Using secret: $SECRET_NAME"
    
    # Get database endpoint (only if not using secret ARN directly)
    if [ -n "$DB_CLUSTER_ID" ]; then
        PGHOST=$(aws rds describe-db-cluster-endpoints \
            --db-cluster-identifier $DB_CLUSTER_ID \
            --region $AWS_REGION \
            --query 'DBClusterEndpoints[0].Endpoint' \
            --output text)
        
        if [ -z "$PGHOST" ]; then
            echo "Failed to retrieve DB endpoint. Check the cluster identifier and permissions."
            return 1
        fi
        export PGHOST
        echo "DB Host: $PGHOST"
    fi
    
    # Get credentials from secret
    CREDS=$(aws secretsmanager get-secret-value \
        --secret-id $SECRET_NAME \
        --region $AWS_REGION)

    if [ $? -ne 0 ]; then
        echo "Failed to retrieve secret. Error:"
        echo "$CREDS"
        return 1
    fi

    CREDS=$(echo "$CREDS" | jq -r '.SecretString')

    if [ -z "$CREDS" ]; then
        echo "Failed to retrieve credentials from Secrets Manager. Check the secret name and permissions."
        return 1
    fi
    
    PGPASSWORD=$(echo $CREDS | jq -r '.password')
    PGUSER=$(echo $CREDS | jq -r '.username')
    
    # If host is in the secret, use it
    if [ -z "$PGHOST" ]; then
        PGHOST=$(echo $CREDS | jq -r '.host // empty')
        if [ -n "$PGHOST" ]; then
            export PGHOST
            echo "DB Host from secret: $PGHOST"
        fi
    fi

    if [ -z "$PGPASSWORD" ] || [ -z "$PGUSER" ]; then
        echo "Failed to extract username or password from the secret."
        return 1
    fi

    export PGPASSWORD
    export PGUSER

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

    # Install Python 3
    sudo yum remove -y openssl-devel > ${TERM} 2>&1
    sudo yum install -y gcc openssl11-devel bzip2-devel libffi-devel sqlite-devel > ${TERM} 2>&1

    echo "Checking if python${PYTHON_MAJOR_VERSION} is already installed"
    if command -v python${PYTHON_MAJOR_VERSION} &> /dev/null; then 
        echo "Python${PYTHON_MAJOR_VERSION} already exists"
        return
    fi

    cd /tmp
    echo "Downloading Python ${PYTHON_VERSION}"
    wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz > ${TERM} 2>&1 || { echo "Failed to download Python"; return 1; }
    tar xzf Python-${PYTHON_VERSION}.tgz > ${TERM} 2>&1 || { echo "Failed to extract Python"; return 1; }
    cd Python-${PYTHON_VERSION}
    echo "Configuring Python"
    ./configure --enable-optimizations > ${TERM} 2>&1 || { echo "Failed to configure Python"; return 1; }
    echo "Building Python (this may take a while)"
    sudo make altinstall > ${TERM} 2>&1 || { echo "Failed to build Python"; return 1; }
    cd /tmp
    sudo rm -rf Python-${PYTHON_VERSION} Python-${PYTHON_VERSION}.tgz

    echo "Updating Python symlinks"
    sudo ln -sf /usr/local/bin/python${PYTHON_MAJOR_VERSION} /usr/bin/python3
    sudo ln -sf /usr/local/bin/pip${PYTHON_MAJOR_VERSION} /usr/bin/pip3

    echo "Upgrading pip"
    /usr/local/bin/python${PYTHON_MAJOR_VERSION} -m pip install --upgrade pip > ${TERM} 2>&1

    echo "Python ${PYTHON_VERSION} installation completed"
}

function activate_venv()
{
    local venv_path="/workshop/${BLAIZE_PROJ_NAME}/venv-blaize-bazaar/bin/activate"

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
        ENV_FILE="/workshop/${BLAIZE_PROJ_NAME}/.env"
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
export PATH="$PATH:$HOME/.local/bin"
export NEXT_TELEMETRY_DISABLED=1
export PS1="\u@\h:\w\$ "

# Python paths
export PATH="/home/participant/.local/bin:/usr/local/bin:$PATH"
export PYTHONPATH="/home/participant/.local/lib/python3.11/site-packages:/home/participant/.local/lib/python3.9/site-packages:$PYTHONPATH"

# Python aliases
alias python="/usr/local/bin/python3"
alias python3="/usr/local/bin/python3"
alias pip="/usr/local/bin/pip3"
alias pip3="/usr/local/bin/pip3"
alias streamlit="python3 -m streamlit"
EOF

    echo "Code Editor bashrc configuration complete"
}

function create_database_test_script() {
    if [ "$ENV_TYPE" != "code-editor" ]; then
        return 0
    fi
    
    echo "Creating database connection test script..."
    
    cat > /workshop/test_connection.py << 'EOFTEST'
#!/usr/bin/env python3
"""
Test script for verifying database connection and pgvector setup
"""
import os
import json
import sys

def test_connection():
    print("=" * 60)
    print("🔍 Testing Aurora PostgreSQL Connection...")
    print("=" * 60)

    # Check for required environment variables
    if not os.environ.get('PGHOST'):
        print("❌ Database not configured (PGHOST not set)")
        print("=" * 60)
        return False

    try:
        import boto3
        import psycopg2
        from pgvector.psycopg2 import register_vector
    except ImportError as e:
        print(f"❌ Missing required Python package: {e}")
        print("=" * 60)
        return False

    try:
        dbhost = os.environ.get('PGHOST')
        dbport = os.environ.get('PGPORT', '5432')
        dbuser = os.environ.get('PGUSER')
        dbpass = os.environ.get('PGPASSWORD')
        dbname = os.environ.get('PGDATABASE', 'postgres')
        region = os.environ.get('AWS_REGION', 'us-west-2')

        print(f"📊 Connection Details:")
        print(f"   Region: {region}")
        print(f"   Host: {dbhost}")
        print(f"   Port: {dbport}")
        print(f"   Database: {dbname}")
        print(f"   User: {dbuser}")
        print("-" * 60)

        conn = psycopg2.connect(
            host=dbhost,
            user=dbuser,
            password=dbpass,
            port=dbport,
            database=dbname,
            connect_timeout=10
        )
        register_vector(conn)

        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ Successfully connected to Aurora PostgreSQL!")
        print(f"   Version: {version[0].split(',')[0]}")

        cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        if cur.fetchone():
            print(f"✅ pgvector extension is installed and ready")
        else:
            print(f"⚠️  pgvector extension is NOT installed")

        print("-" * 60)
        print(f"🔗 Connection String:")
        print(f"   postgresql://{dbuser}:****@{dbhost}:{dbport}/{dbname}")
        print("-" * 60)
        print(f"💡 Quick psql commands:")
        print(f"   psql                         - Connect to database")
        print(f"   psql -c 'SELECT version()'   - Check version")

        cur.close()
        conn.close()

        print("=" * 60)
        print("✅ Database connection test PASSED!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"❌ Database connection FAILED: {e}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
EOFTEST

    chmod +x /workshop/test_connection.py
    chown $WORKSHOP_USER:$WORKSHOP_USER /workshop/test_connection.py
    echo "Database test script created at /workshop/test_connection.py"
}

function create_streamlit_fix_script() {
    if [ "$ENV_TYPE" != "code-editor" ]; then
        return 0
    fi
    
    echo "Creating Streamlit fix script..."
    
    cat > /workshop/fix_streamlit.sh << 'EOFFIX'
#!/bin/bash
echo "🔧 Comprehensive Streamlit Fix Script"
echo "======================================"

# Function to test streamlit
test_streamlit() {
  local python_cmd=$1
  echo "Testing Streamlit with $python_cmd..."
  if $python_cmd -c "import streamlit; print('Streamlit version:', streamlit.__version__)" 2>/dev/null; then
    echo "✅ Streamlit is working with $python_cmd"
    return 0
  else
    echo "❌ Streamlit not working with $python_cmd"
    return 1
  fi
}

# Try different Python commands
PYTHON_COMMANDS=("python" "python3" "/usr/local/bin/python" "/usr/local/bin/python3" "python3.11" "python3.9")

echo "Step 1: Testing existing Streamlit installations..."
for cmd in "${PYTHON_COMMANDS[@]}"; do
  if command -v $cmd &> /dev/null; then
    if test_streamlit $cmd; then
      echo "✅ Streamlit already working with $cmd"
      echo "Use: $cmd -m streamlit run Home.py --server.port 8501"
      exit 0
    fi
  fi
done

echo "Step 2: Installing Streamlit..."
cd /workshop/blaize-bazaar 2>/dev/null || cd /workshop

# Try virtual environment first
if [ -d "venv-blaize-bazaar" ]; then
  echo "Using virtual environment..."
  source venv-blaize-bazaar/bin/activate
  python -m pip install --upgrade pip
  python -m pip install --force-reinstall streamlit plotly altair pandas
  if test_streamlit python; then
    echo "✅ Success! Use: source venv-blaize-bazaar/bin/activate && streamlit run Home.py --server.port 8501"
    exit 0
  fi
  deactivate
fi

# Try system installation
echo "Trying system installation..."
for cmd in "${PYTHON_COMMANDS[@]}"; do
  if command -v $cmd &> /dev/null; then
    echo "Installing with $cmd..."
    $cmd -m pip install --user --force-reinstall streamlit plotly altair pandas
    if test_streamlit $cmd; then
      echo "✅ Success! Use: $cmd -m streamlit run Home.py --server.port 8501"
      exit 0
    fi
  fi
done

echo "❌ All installation attempts failed"
echo "Manual steps:"
echo "1. Check Python: python3 --version"
echo "2. Install manually: python3 -m pip install --user streamlit"
echo "3. Run with: python3 -m streamlit run Home.py --server.port 8501"
EOFFIX

    chmod +x /workshop/fix_streamlit.sh
    chown $WORKSHOP_USER:$WORKSHOP_USER /workshop/fix_streamlit.sh
    echo "Streamlit fix script created at /workshop/fix_streamlit.sh"
}

function create_startup_script() {
    if [ "$ENV_TYPE" != "code-editor" ]; then
        return 0
    fi
    
    echo "Creating startup check script..."
    
    cat > $HOME/.startup_check.sh << 'EOFSTARTUP'
#!/bin/bash
clear
echo ""
echo "🚀 Welcome to GenAI pgvector Workshop!"
echo ""

# Test database connection if available
if [ -f /workshop/test_connection.py ] && [ -n "$PGHOST" ]; then
    python3 /workshop/test_connection.py
fi

echo ""
echo "📚 Quick Start Guide:"
echo "   1. 🔐 Bedrock models are pre-configured"
echo "   2. 📖 Follow the lab instructions"
echo "   3. 🎯 Navigate to blaize-bazaar for advanced labs"
echo ""
echo "📊 Database Commands:"
echo "   psql                         - Connect to Aurora PostgreSQL"
echo "   python3 test_connection.py   - Test database connection"
echo ""
echo "🐍 Python Version: $(python3 --version 2>&1)"
echo ""
if [ -d "/workshop/blaize-bazaar" ]; then
    echo "🛍️ Blaize Bazaar: Ready for advanced labs"
    if [ -f "/workshop/blaize-bazaar/venv-blaize-bazaar/bin/activate" ]; then
        echo "   cd blaize-bazaar && source venv-blaize-bazaar/bin/activate && streamlit run Home.py --server.port 8501"
    else
        echo "   cd blaize-bazaar && python3 -m streamlit run Home.py --server.port 8501"
    fi
    echo ""
fi
echo "Happy coding! 🎉"
echo ""
EOFSTARTUP
    
    chmod +x $HOME/.startup_check.sh
    
    # Add to bashrc
    cat >> $HOME/.bashrc << 'EOFBASHRC'

# Run startup check on first terminal
if [ -z $STARTUP_CHECK_DONE ]; then
    export STARTUP_CHECK_DONE=1
    ~/.startup_check.sh
fi

# Ensure terminal starts in workshop directory
if [ "$PWD" != "/workshop" ] && [ -d "/workshop" ]; then
    cd /workshop
fi

# Auto-activate Blaize Bazaar virtual environment if available
if [ -f "/workshop/blaize-bazaar/venv-blaize-bazaar/bin/activate" ] && [ -z "$VIRTUAL_ENV" ]; then
    source /workshop/blaize-bazaar/venv-blaize-bazaar/bin/activate
fi
EOFBASHRC

    echo "Startup script created and configured"
}

function create_workshop_readme() {
    if [ "$ENV_TYPE" != "code-editor" ]; then
        return 0
    fi
    
    echo "Creating workshop README..."
    
    cat > /workshop/README.md << EOFREADME
# Welcome to the GenAI pgvector Workshop! 🚀

## 🗄️ Database Connection

Your Aurora PostgreSQL database is automatically configured and ready to use!

### Quick Database Commands:
\`\`\`bash
# Connect to PostgreSQL
psql

# Test database connection
python3 test_connection.py
\`\`\`

### Common psql Commands:
\`\`\`sql
-- Once connected to psql:
\l              -- List databases
\dt             -- List tables
\dx             -- List extensions
\d table_name   -- Describe table
\q              -- Quit psql
\`\`\`

## 🎯 Getting Started

### 📋 Step 1: Enable Bedrock Model Access
Before starting the lab, ensure you have enabled access to the required Bedrock models:
1. Open the AWS Console in a new tab
2. Navigate to Amazon Bedrock
3. Go to "Model access" in the left menu
4. Enable access to:
   - Amazon Titan Embeddings V2
   - Claude 3.5 Sonnet
   - Other models as specified in your lab guide

### 📚 Step 2: Follow Lab Instructions
Your workshop includes modules for:
- Aurora PostgreSQL with pgvector setup
- Semantic search implementation
- Product recommendations
- AI-powered applications

## ℹ️ Environment Info
- **Python**: 3.11 (default)
- **PostgreSQL Client**: 16 (or 15)
- **Database**: Aurora PostgreSQL 16 with pgvector
- **Region**: ${AWS_REGION}
- **Theme**: Dark mode enabled
- **Git**: Disabled for workshop

## 📚 Helpful Resources
- Database credentials are stored in AWS Secrets Manager
- All required Python libraries are pre-installed
- PostgreSQL connection is auto-configured on terminal start

## 🔧 Troubleshooting

### Streamlit Not Found?
If you get "streamlit: command not found":
\`\`\`bash
# Option 1: Use the fix script
./fix_streamlit.sh

# Option 2: Manual fix
cd blaize-bazaar
source venv-blaize-bazaar/bin/activate  # if virtual env exists
python3 -m pip install streamlit plotly altair

# Option 3: Use python module directly
python3 -m streamlit run Home.py --server.port 8501
\`\`\`

### Python Command Not Found?
\`\`\`bash
# Use full path or python3
/usr/local/bin/python3 --version
python3 --version
\`\`\`

Happy coding! 🎉
EOFREADME
    
    chmod 644 /workshop/README.md
    chown $WORKSHOP_USER:$WORKSHOP_USER /workshop/README.md
    echo "Workshop README created at /workshop/README.md"
}

function check_installation()
{
    overall="True"
    
    # Check AWS Region
    if [ -z "$AWS_REGION" ]; then
        echo "AWS Region not set : NOTOK"
        overall="False"
    else
        echo "AWS Region set to $AWS_REGION : OK"
    fi
    
    # Check AWS CLI
    if aws sts get-caller-identity &> /dev/null; then
        echo "AWS CLI configuration : OK"
    else
        echo "AWS CLI configuration : NOTOK"
        overall="False"
    fi
    
    # Check PostgreSQL
    if psql -c "select version()" | grep -q PostgreSQL; then
        echo "PostgreSQL installation : OK"
    else
        echo "PostgreSQL installation : NOTOK"
        echo "Error: $(psql -c "select version()" 2>&1)"
        overall="False"
    fi
    
    # Check PostgreSQL Configuration
    if [ -n "$PGHOST" ] && [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ]; then
        echo "PostgreSQL configuration : OK"
    else
        echo "PostgreSQL configuration : NOTOK (may be normal if no database)"
    fi
    
    # Check Main Project Directory
    MAIN_PROJ_DIR="${HOME}/environment/${PROJ_NAME}"
    if [ "$ENV_TYPE" == "code-editor" ]; then
        MAIN_PROJ_DIR="/workshop/${PROJ_NAME}"
    fi
    
    if [ -d "$MAIN_PROJ_DIR" ]; then 
        echo "Main project directory : OK"
    else
        echo "Main project directory : NOTOK (optional)"
    fi

    # Check Blaize Bazaar Project Directory (optional)
    if [ -d "/workshop/${BLAIZE_PROJ_NAME}/" ]; then 
        echo "Blaize Bazaar project directory : OK"
    else
        echo "Blaize Bazaar project directory : NOTOK (optional)"
    fi

    # Check Python Installation
    if command -v python${PYTHON_MAJOR_VERSION} &> /dev/null; then
        echo "Python${PYTHON_MAJOR_VERSION} installation : OK"
        python${PYTHON_MAJOR_VERSION} --version
    else
        echo "Python${PYTHON_MAJOR_VERSION} installation : NOTOK"
        echo "Error: python${PYTHON_MAJOR_VERSION} command not found"
        overall="False"
    fi

    # Check Python3 Symlink
    if command -v python3 &> /dev/null; then
        echo "Python3 symlink : OK"
        python3 --version
    else
        echo "Python3 symlink : NOTOK"
        echo "Error: python3 command not found"
        overall="False"
    fi

    # Check Virtual Environment (optional for Blaize Bazaar)
    if [ -f "/workshop/${BLAIZE_PROJ_NAME}/venv-blaize-bazaar/bin/activate" ]; then
        echo "Blaize Bazaar virtual environment : OK"
        
        # Check Required Python Packages
        echo "Checking required Python packages..."
        source "/workshop/${BLAIZE_PROJ_NAME}/venv-blaize-bazaar/bin/activate" &> /dev/null
        required_packages=("psycopg2" "boto3" "pandas" "numpy" "streamlit")
        for package in "${required_packages[@]}"; do
            if ! pip show "$package" &> /dev/null; then
                echo "Python package $package : NOTOK"
                overall="False"
            else
                echo "Python package $package : OK"
            fi
        done
        deactivate
    else
        echo "Blaize Bazaar virtual environment : NOTOK (optional)"
    fi

    # Check Bedrock and S3 environment variables (optional)
    if [ -n "$S3_KB_BUCKET" ] && [ -n "$BEDROCK_KB_ID" ] && [ -n "$BEDROCK_AGENT_ID" ] && [ -n "$BEDROCK_AGENT_ALIAS_ID" ]; then
        echo "Bedrock and S3 environment variables : OK"
    else
        echo "Bedrock and S3 environment variables : NOTOK (optional)"
    fi

    # Code Editor specific checks
    if [ "$ENV_TYPE" == "code-editor" ]; then
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
        
        if [ -f "$HOME/.startup_check.sh" ]; then
            echo "Startup check script : OK"
        else
            echo "Startup check script : NOTOK"
        fi
    fi

    echo "=================================="
    if [ "${overall}" == "True" ]; then
        echo "✅ Overall status : OK"
    else
        echo "⚠️  Overall status : FAILED (some optional components may be missing)"
    fi
    echo "=================================="
}

function cp_logfile()
{
    log_file="/tmp/bootstrap.log"
    bucket_name="genai-pgv-labs-${AWS_ACCOUNT_ID}-`date +%s`"
    echo ${bucket_name}
    aws s3 ls | grep ${bucket_name} > /dev/null 2>&1
    if [ $? -ne 0 ] ; then
        aws s3 mb s3://${bucket_name} --region ${AWS_REGION}
    fi

    aws s3 cp ${log_file} s3://${bucket_name}/prereq_${AWS_ACCOUNT_ID}.txt > /dev/null 
    if [ $? -eq 0 ] ; then
	echo "Copied the logfile to bucket ${bucket_name}"
    else
	echo "Failed to copy logfile to bucket ${bucket_name}"
    fi
}

##############################################
# MAIN PROGRAM
##############################################

if [ "${1}X" == "-xX" ] ; then
    TERM="/dev/tty"
else
    TERM="/dev/null"
fi

echo "=========================================="
echo "GenAI pgvector Workshop Prerequisites"
echo "Environment: $ENV_TYPE"
echo "User: $WORKSHOP_USER"
echo "=========================================="
echo "Process started at `date`"
echo ""

check_aws_cli || { echo "AWS CLI check failed"; exit 1; }
install_packages || { echo "install_packages check failed"; exit 1; }

export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text) 

print_line
git_clone
print_line
install_postgresql
configure_pg
print_line
install_python3
print_line
setup_venv
print_line
set_bedrock_env_vars
print_line

# Code Editor specific setup
if [ "$ENV_TYPE" == "code-editor" ]; then
    echo "Running Code Editor specific setup..."
    setup_code_editor_bashrc
    create_database_test_script
    create_streamlit_fix_script
    create_startup_script
    create_workshop_readme
    print_line
fi

check_installation
cp_logfile

# Activate virtual environment as the last step (if available)
activate_venv

echo ""
echo "=========================================="
echo "✅ Process completed at `date`"
echo "=========================================="
