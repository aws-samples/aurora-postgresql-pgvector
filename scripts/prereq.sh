#!/bin/bash

# Ensure HOME is set
if [ -z "$HOME" ]; then
    export HOME=$(getent passwd $(id -un) | cut -d: -f6)
fi

# Main repository configuration (keep original)
export DefaultCodeRepository="https://github.com/aws-samples/aurora-postgresql-pgvector.git"
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
    local clone_dir="${HOME}/environment"
    cd "$clone_dir" || { echo "Failed to change directory to $clone_dir"; return 1; }
    
    # Clone main repository
    if [ -d "$PROJ_NAME" ]; then
        echo "Directory $PROJ_NAME already exists. Removing it before cloning."
        sudo rm -rf "$PROJ_NAME"
    fi
    git clone "$DefaultCodeRepository" || { echo "Failed to clone main repository"; return 1; }
    echo "Successfully cloned main repository"
    
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
    sudo chown -R $(whoami):$(whoami) "$workshop_dir" 2>/dev/null || true
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
    
    echo "Found secret: $SECRET_NAME"
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

    # Persist values for future sessions
    echo "export PGUSER='$PGUSER'" >> ~/.bash_profile
    echo "export PGPASSWORD='$PGPASSWORD'" >> ~/.bash_profile
    echo "export PGHOST='$PGHOST'" >> ~/.bash_profile
    echo "export AWS_REGION='$AWS_REGION'" >> ~/.bash_profile
    echo "export AWSREGION='$AWS_REGION'" >> ~/.bash_profile
    echo "export PGDATABASE='postgres'" >> ~/.bash_profile
    echo "export PGPORT=5432" >> ~/.bash_profile
    echo "export DB_NAME=postgres" >> ~/.bash_profile
    echo "export PGVECTOR_DRIVER='psycopg2'" >> ~/.bash_profile
    echo "export PGVECTOR_USER='$PGUSER'" >> ~/.bash_profile
    echo "export PGVECTOR_PASSWORD='$PGPASSWORD'" >> ~/.bash_profile
    echo "export PGVECTOR_HOST='$PGHOST'" >> ~/.bash_profile
    echo "export PGVECTOR_PORT=5432" >> ~/.bash_profile
    echo "export PGVECTOR_DATABASE='postgres'" >> ~/.bash_profile

    source ~/.bash_profile

    echo "Environment variables set and persisted"

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
    
    # Only proceed if we have some Bedrock variables (not all may be available)
    if [ -n "$S3_KB_BUCKET" ] || [ -n "$BEDROCK_KB_ID" ] || [ -n "$BEDROCK_AGENT_ID" ]; then
        # Write variables to .bash_profile
        echo "Writing Bedrock variables to .bash_profile..."
        {
            echo "# Bedrock KB and S3 environment variables"
            [ -n "$S3_KB_BUCKET" ] && echo "export S3_KB_BUCKET='${S3_KB_BUCKET}'"
            [ -n "$BEDROCK_KB_ID" ] && echo "export BEDROCK_KB_ID='${BEDROCK_KB_ID}'"
            [ -n "$BEDROCK_AGENT_ID" ] && echo "export BEDROCK_AGENT_ID='${BEDROCK_AGENT_ID}'"
            [ -n "$BEDROCK_AGENT_ALIAS_ID" ] && echo "export BEDROCK_AGENT_ALIAS_ID='${BEDROCK_AGENT_ALIAS_ID}'"
        } >> ~/.bash_profile
        
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
        
        # Source the updated .bash_profile to make variables available immediately
        source ~/.bash_profile
        
        echo "Bedrock environment variables set successfully"
    else
        echo "No Bedrock CloudFormation outputs found (this is normal for basic setups)"
    fi
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
        echo "PostgreSQL configuration : NOTOK"
        overall="False"
    fi
    
    # Check Main Project Directory
    if [ -d "${HOME}/environment/${PROJ_NAME}/" ]; then 
        echo "Main project directory : OK"
    else
        echo "Main project directory : NOTOK"
        echo "Error: Directory ${HOME}/environment/${PROJ_NAME}/ does not exist"
        overall="False"
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
        required_packages=("psycopg" "boto3" "pandas" "numpy" "streamlit")
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

    echo "=================================="
    if [ "${overall}" == "True" ]; then
        echo "Overall status : OK"
    else
        echo "Overall status : FAILED"
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

# Main program starts here

if [ "${1}X" == "-xX" ] ; then
    TERM="/dev/tty"
else
    TERM="/dev/null"
fi

echo "Process started at `date`"

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
check_installation
cp_logfile

# Activate virtual environment as the last step (if available)
activate_venv

echo "Process completed at `date`"
