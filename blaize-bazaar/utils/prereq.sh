#!/bin/bash

# Ensure HOME is set
if [ -z "$HOME" ]; then
    export HOME=$(getent passwd $(id -un) | cut -d: -f6)
fi

export DefaultCodeRepository="https://github.com/aws-samples/DAT301-reinvent-2024.git"
export PROJ_NAME="DAT301-reinvent-2024"
export PYTHON_MAJOR_VERSION="3.11"
export PYTHON_MINOR_VERSION="9"
export PYTHON_VERSION="${PYTHON_MAJOR_VERSION}.${PYTHON_MINOR_VERSION}"

export AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
echo "Setting AWS Region to: $AWS_REGION"

echo "export AWS_REGION='$AWS_REGION'" >> ~/.bashrc
source ~/.bashrc

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

function create_env_file() 
{
    local repo_dir="${HOME}/environment/${PROJ_NAME}"
    local env_file="${repo_dir}/.env"
    # Ensure we're in the repository directory
    cd "$repo_dir" || { echo "Failed to change directory to $repo_dir"; return 1; }
    # Create or overwrite the .env file
    cat > "$env_file" << EOL
# Database configuration
# Note: Don't change these values
DB_HOST=${PGHOST}
DB_PORT=${PGPORT}
DB_NAME=${PGDATABASE}
DB_USER=${PGUSER}
DB_PASSWORD=${PGPASSWORD}
    
# AWS configuration
# Note: Don't change these values
AWS_REGION=${AWS_REGION}

# Bedrock configuration
# Note: Don't change these values
BEDROCK_CLAUDE_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
BEDROCK_CLAUDE_MODEL_ARN=arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0

# Lambda configuration
# Note: Don't change this value
LAMBDA_FUNCTION_NAME=genai-dat-301-labs_BedrockAgent_Lambda
EOL
    
    echo "Created .env file at $env_file"
    # Optionally, you can print the contents of the file (be careful with sensitive information)
    cat "$env_file"
}

function git_clone()
{
    local clone_dir="${HOME}/environment"
    cd "$clone_dir" || { echo "Failed to change directory to $clone_dir"; return 1; }

    local repo_name=$(basename "$DefaultCodeRepository" .git)

    if [ -d "$repo_name" ]; then
        echo "Directory $repo_name already exists. Removing it before cloning."
        rm -rf "$repo_name" || { echo "Failed to remove existing directory"; return 1; }
    fi

    git clone "$DefaultCodeRepository" || { echo "Failed to clone repository"; return 1; }
    echo "Successfully cloned repository"

    # Change to the newly cloned repository directory
    cd "$repo_name" || { echo "Failed to change directory to $repo_name"; return 1; }

    # Create .gitignore file
    echo "Creating .gitignore file..."
    cat > .gitignore << 'EOL'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
venv-*/
*.egg
*.egg-info/
.env
# Cloud9
.c9/
*.launch
.settings/
# Misc
.DS_Store
.idea/
.vscode/
*.swp
*.swo
.coverage
htmlcov/
.pytest_cache/
.ipynb_checkpoints/
# AWS
.aws/
.aws-sam/
EOL

    # Create .env file
    create_env_file || { echo "Failed to create .env file"; return 1; }

    # Create virtual environment
    python3 -m venv "./venv-blaize-bazaar" || { echo "Failed to create virtual environment"; return 1; }

    # Activate virtual environment and install requirements
    source "./venv-blaize-bazaar/bin/activate" || { echo "Failed to activate virtual environment"; return 1; }
    python3 -m pip install -r requirements.txt || { echo "Failed to install requirements"; return 1; }
    deactivate

    echo "Successfully set up virtual environment and installed requirements"
}

function print_line()
{
    echo "---------------------------------"
}

function resize_cloud9() {
    echo "Resizing Cloud9 volume..."
    # Specify the desired volume size in GiB as a command line argument. If not specified, default to 50 GiB.
    SIZE=${1:-50}

    # Get the ID of the environment host Amazon EC2 instance.
    INSTANCEID=$(curl --silent http://169.254.169.254/latest/meta-data/instance-id)
    echo "Instance ID: $INSTANCEID"

    # Get the ID of the Amazon EBS volume associated with the instance.
    VOLUMEID=$(aws ec2 describe-instances \
        --instance-id $INSTANCEID \
        --query "Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId" \
        --output text)

    if [ -z "$VOLUMEID" ]; then
        echo "Error: Failed to get volume ID"
        return 1
    fi
    echo "Volume ID: $VOLUMEID"

    # Check the current volume size
    CURRENT_VOLSIZE=$(aws ec2 describe-volumes \
        --volume-ids $VOLUMEID \
        --query "Volumes[0].Size" \
        --output text)

    echo "Current volume size: $CURRENT_VOLSIZE GB"
    echo "Requested volume size: $SIZE GB"

    if [ "$SIZE" -le "$CURRENT_VOLSIZE" ]; then
        echo "Skipping: Current volume size ($CURRENT_VOLSIZE GB) is greater than or equal to requested size ($SIZE GB)"
        return 0
    fi

    echo "Resizing volume..."
    # Resize the EBS volume.
    aws ec2 modify-volume --volume-id $VOLUMEID --size $SIZE

    echo "Waiting for resize to complete..."
    while true; do
        STATE=$(aws ec2 describe-volumes-modifications \
            --volume-id $VOLUMEID \
            --filters Name=modification-state,Values="optimizing","completed" \
            --query "length(VolumesModifications)" \
            --output text)
        
        if [ "$STATE" = "1" ]; then
            echo "Volume modification complete"
            break
        fi
        echo "Still waiting..."
        sleep 1
    done

    echo "Checking file system..."
    #Check if we're on an NVMe filesystem
    if [ "$(readlink -f /dev/xvda)" = "/dev/xvda" ]; then
        echo "Standard EBS volume detected"
        # Rewrite the partition table so that the partition takes up all the space that it can.
        sudo growpart /dev/xvda 1
        
        # Expand the size of the file system.
        # Check if we are on AL2
        if grep -q "VERSION_ID=\"2\"" /etc/os-release; then
            echo "Amazon Linux 2 detected, using xfs_growfs"
            sudo xfs_growfs -d /
        else
            echo "Using resize2fs"
            sudo resize2fs /dev/xvda1
        fi
    else
        echo "NVMe volume detected"
        # Rewrite the partition table so that the partition takes up all the space that it can.
        sudo growpart /dev/nvme0n1 1
        
        # Expand the size of the file system.
        # Check if we're on AL2
        if grep -q "VERSION_ID=\"2\"" /etc/os-release; then
            echo "Amazon Linux 2 detected, using xfs_growfs"
            sudo xfs_growfs -d /
        else
            echo "Using resize2fs"
            sudo resize2fs /dev/nvme0n1p1
        fi
    fi

    echo "Volume resize completed successfully!"
    df -h /
}

function install_packages()
{
    local current_dir
    current_dir=$(pwd)
    
    sudo yum install -y jq  > "${TERM}" 2>&1
    print_line
    
    # Resize Cloud9 to 50GB
    resize_cloud9 50
    
    print_line
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

    # Enable PostgreSQL14 as part of amazon-extras library
    sudo amazon-linux-extras enable postgresql14
    sudo yum install -y postgresql-server > ${TERM} 2>&1

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

    # Use already set AWS_REGION or fetch from metadata if not set
    if [ -z "$AWS_REGION" ]; then
        export AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
        echo "AWS Region not set, fetched from metadata: $AWS_REGION"
    else
        echo "Using existing AWS Region: $AWS_REGION"
    fi
    
    # Print current IAM role information
    echo "Current IAM role:"
    aws sts get-caller-identity

    DB_CLUSTER_ID="apg-pgvector-riv"
    echo "Retrieving DB endpoint for cluster: $DB_CLUSTER_ID"
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
    
    # Retrieve credentials from Secrets Manager
    SECRET_NAME="apg-pgvector-secret-RIV"
    echo "Retrieving secret: $SECRET_NAME"
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

    # Persist values for future sessions
    echo "export PGUSER='$PGUSER'" >> ~/.bash_profile
    echo "export PGPASSWORD='$PGPASSWORD'" >> ~/.bash_profile
    echo "export PGHOST='$PGHOST'" >> ~/.bash_profile
    echo "export AWS_REGION='$AWS_REGION'" >> ~/.bash_profile
    echo "export PGDATABASE='postgres'" >> ~/.bash_profile
    echo "export PGPORT=5432" >> ~/.bash_profile

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
    local clone_dir="${HOME}/environment"
    local repo_name=$(basename "$DefaultCodeRepository" .git)
    local venv_path="${clone_dir}/${repo_name}/venv-blaize-bazaar/bin/activate"

    if [ -f "$venv_path" ]; then
        echo "Activating virtual environment"
        source "$venv_path" || { echo "Failed to activate virtual environment"; return 1; }
        echo "Virtual environment activated successfully"
    else
        echo "Virtual environment not found at $venv_path"
        return 1
    fi
}

function set_bedrock_env_vars() {
    echo "Setting Bedrock and S3 environment variables from CloudFormation outputs..."
    
    # Get values directly from CloudFormation outputs without specifying stack name
    export S3_KB_BUCKET=$(aws cloudformation describe-stacks \
        --query "Stacks[].Outputs[?(OutputKey == 'BedrockS3Bucket')][].{OutputValue:OutputValue}" --output text)
    
    export BEDROCK_KB_ID=$(aws cloudformation describe-stacks \
        --query "Stacks[].Outputs[?(OutputKey == 'BedrockKnowledgeBaseId')][].{OutputValue:OutputValue}" --output text)
    
    export BEDROCK_AGENT_ID=$(aws cloudformation describe-stacks \
        --query "Stacks[].Outputs[?(OutputKey == 'BedrockAgentId')][].{OutputValue:OutputValue}" --output text)
    
    # Get full alias ID and extract the actual alias part
    local FULL_ALIAS_ID=$(aws cloudformation describe-stacks \
        --query "Stacks[].Outputs[?(OutputKey == 'BedrockAgentAliasId')][].{OutputValue:OutputValue}" --output text)
    
    if [ -n "$FULL_ALIAS_ID" ]; then
        export BEDROCK_AGENT_ALIAS_ID=$(echo "$FULL_ALIAS_ID" | cut -d'|' -f2)
    fi
    
    # Verify all variables were set
    if [ -z "$S3_KB_BUCKET" ] || [ -z "$BEDROCK_KB_ID" ] || [ -z "$BEDROCK_AGENT_ID" ] || [ -z "$BEDROCK_AGENT_ALIAS_ID" ]; then
        echo "Error: One or more required variables could not be retrieved:"
        echo "S3_KB_BUCKET: ${S3_KB_BUCKET:-NOT SET}"
        echo "BEDROCK_KB_ID: ${BEDROCK_KB_ID:-NOT SET}"
        echo "BEDROCK_AGENT_ID: ${BEDROCK_AGENT_ID:-NOT SET}"
        echo "BEDROCK_AGENT_ALIAS_ID: ${BEDROCK_AGENT_ALIAS_ID:-NOT SET}"
        return 1
    fi
    
    # Write variables to .bashrc
    echo "Writing variables to .bashrc..."
    {
        echo "# Bedrock KB and S3 environment variables"
        echo "export S3_KB_BUCKET='${S3_KB_BUCKET}'"
        echo "export BEDROCK_KB_ID='${BEDROCK_KB_ID}'"
        echo "export BEDROCK_AGENT_ID='${BEDROCK_AGENT_ID}'"
        echo "export BEDROCK_AGENT_ALIAS_ID='${BEDROCK_AGENT_ALIAS_ID}'"
    } >> ~/.bashrc
    
    # Append to the .env file if it exists
    ENV_FILE="${HOME}/environment/${PROJ_NAME}/.env"
    if [ -f "$ENV_FILE" ]; then
        echo "Appending Bedrock and S3 variables to .env file..."
        {
            echo ""
            echo "# Bedrock and S3 configuration"
            echo "S3_KB_BUCKET=${S3_KB_BUCKET}"
            echo "BEDROCK_KB_ID=${BEDROCK_KB_ID}"
            echo "BEDROCK_AGENT_ID=${BEDROCK_AGENT_ID}"
            echo "BEDROCK_AGENT_ALIAS_ID=${BEDROCK_AGENT_ALIAS_ID}"
        } >> "$ENV_FILE"
        
        echo "Variables successfully appended to .env file"
    else
        echo "Warning: .env file not found at $ENV_FILE"
    fi
    
    # Source the updated .bashrc to make variables available immediately
    source ~/.bashrc
    
    echo "Environment variables set and persisted successfully:"
    echo "S3_KB_BUCKET: ${S3_KB_BUCKET}"
    echo "BEDROCK_KB_ID: ${BEDROCK_KB_ID}"
    echo "BEDROCK_AGENT_ID: ${BEDROCK_AGENT_ID}"
    echo "BEDROCK_AGENT_ALIAS_ID: ${BEDROCK_AGENT_ALIAS_ID}"
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
    
    # Check Git Clone
    if [ -d "${HOME}/environment/${PROJ_NAME}/" ]; then 
        echo "Git Clone : OK"
    else
        echo "Git Clone : NOTOK"
        echo "Error: Directory ${HOME}/environment/${PROJ_NAME}/ does not exist"
        overall="False"
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

    # Check Virtual Environment
    if [ -f "${HOME}/environment/${PROJ_NAME}/venv-blaize-bazaar/bin/activate" ]; then
        echo "Virtual environment setup : OK"
    else
        echo "Virtual environment setup : NOTOK"
        overall="False"
    fi

    # Check Bedrock and S3 environment variables
    if [ -n "$S3_KB_BUCKET" ] && [ -n "$BEDROCK_KB_ID" ] && [ -n "$BEDROCK_AGENT_ID" ] && [ -n "$BEDROCK_AGENT_ALIAS_ID" ]; then
        echo "Bedrock and S3 environment variables : OK"
    else
        echo "Bedrock and S3 environment variables : NOTOK"
        overall="False"
    fi

    # Check Required Python Packages
    echo "Checking required Python packages..."
    source "${HOME}/environment/${PROJ_NAME}/venv-blaize-bazaar/bin/activate" &> /dev/null
    required_packages=("psycopg" "boto3" "pandas" "numpy")
    packages_ok=true
    for package in "${required_packages[@]}"; do
        if ! pip show "$package" &> /dev/null; then
            echo "Python package $package : NOTOK"
            packages_ok=false
            overall="False"
        else
            echo "Python package $package : OK"
        fi
    done
    deactivate

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

# Ensure script runs as ec2-user
if [ "$(id -u -n)" != "ec2-user" ]; then 
  sudo -u ec2-user -i "$0" "$@"
  exit $?
fi

check_aws_cli || { echo "AWS CLI check failed"; exit 1; }
install_packages || { echo "install_packages check failed"; exit 1; }

export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text) 

print_line
install_postgresql
configure_pg
print_line
install_python3
print_line
git_clone
print_line
set_bedrock_env_vars
print_line
check_installation
cp_logfile

# Activate virtual environment as the last step
activate_venv

echo "Process completed at `date`"