#!/bin/bash

export PROJ_NAME="aurora-postgresql-pgvector"
export GITHUB_URL="https://github.com/aws-samples/"
export PYTHON_MAJOR_VERSION="3.11"
export PYTHON_MINOR_VERSION="9"
export PYTHON_VERSION="${PYTHON_MAJOR_VERSION}.${PYTHON_MINOR_VERSION}"

function print_line()
{
    echo "---------------------------------"
}

function install_packages()
{
    sudo yum install -y jq  > ${TERM} 2>&1
    print_line
    source <(curl -s https://raw.githubusercontent.com/aws-samples/aws-swb-cloud9-init/mainline/cloud9-resize.sh)
    echo "Installing aws cli v2"
    print_line
    aws --version | grep aws-cli\/2 > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        cd $current_dir
	return
    fi
    current_dir=`pwd`
    cd /tmp
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" > ${TERM} 2>&1
    unzip -o awscliv2.zip > ${TERM} 2>&1
    sudo ./aws/install --update > ${TERM} 2>&1
    cd $current_dir
}

function install_postgresql()
{
    print_line
    echo "Installing Postgresql client"
    print_line
    sudo amazon-linux-extras install -y postgresql14 > ${TERM} 2>&1
    sudo yum install -y postgresql-contrib sysbench > ${TERM} 2>&1
}

function clone_git()
{
    print_line
    echo "Cloning the git repository"
    print_line
    cd ${HOME}/environment
    git clone ${GITHUB_URL}${PROJ_NAME}
    cd ${PROJ_NAME}
    print_line
}


function configure_pg()
{
    #AWS_REGION=`aws configure get region`

    PGHOST=`aws rds describe-db-cluster-endpoints \
        --db-cluster-identifier apgpg-pgvector \
        --region $AWS_REGION \
        --query 'DBClusterEndpoints[0].Endpoint' \
        --output text`
    export PGHOST

    # Retrieve credentials from Secrets Manager - Secret: apgpg-pgvector-secret
    CREDS=`aws secretsmanager get-secret-value \
        --secret-id apgpg-pgvector-secret \
        --region $AWS_REGION | jq -r '.SecretString'`

    PGPASSWORD="`echo $CREDS | jq -r '.password'`"
    if [ "${PGPASSWORD}X" == "X" ]; then
        PGPASSWORD="postgres"
    fi
    export PGPASSWORD

    PGUSER="postgres"
    PGUSER="`echo $CREDS | jq -r '.username'`"
    if [ "${PGUSER}X" == "X" ]; then
        PGUSER="postgres"
    fi
    export PGUSER

    # Persist values in future terminals
    echo "export PGUSER=$PGUSER" >> /home/ec2-user/.bashrc
    echo "export PGPASSWORD='$PGPASSWORD'" >> /home/ec2-user/.bashrc
    echo "export PGHOST=$PGHOST" >> /home/ec2-user/.bashrc
    echo "export AWS_REGION=$AWS_REGION" >> /home/ec2-user/.bashrc
    echo "export AWSREGION=$AWS_REGION" >> /home/ec2-user/.bashrc
    echo "export PGDATABASE=postgres" >> /home/ec2-user/.bashrc
    echo "export PGPORT=5432" >> /home/ec2-user/.bashrc


    echo "export PGVECTOR_DRIVER='psycopg2'" >> /home/ec2-user/.bashrc
    echo "export PGVECTOR_USER=${PGUSER}" >> /home/ec2-user/.bashrc
    echo "export PGVECTOR_PASSWORD='$PGPASSWORD'" >> /home/ec2-user/.bashrc
    echo "export PGVECTOR_HOST=$PGHOST" >> /home/ec2-user/.bashrc
    echo "export PGVECTOR_PORT=5432" >> /home/ec2-user/.bashrc
    echo "export PGVECTOR_DATABASE='postgres'" >> /home/ec2-user/.bashrc
}

function install_extension()
{
    psql -h ${PGHOST} -c "create extension if not exists vector"
}

function install_python3()
{
    # Install Python 3
    sudo yum remove -y openssl-devel > ${TERM} 2>&1
    sudo yum install -y gcc openssl11-devel bzip2-devel libffi-devel  > ${TERM} 2>&1

    echo "Checking if python${PYTHON_MAJOR_VERSION} is already installed"
    if [ -f /usr/local/bin/python${PYTHON_MAJOR_VERSION} ] ; then 
        echo "Python${PYTHON_MAJOR_VERSION} already exists"
	return
    fi

    cd /opt
    echo "Installing python ${PYTHON_VERSION}"
    sudo wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz  > ${TERM} 2>&1
    sudo tar xzf Python-${PYTHON_VERSION}.tgz  > ${TERM} 2>&1
    cd Python-${PYTHON_VERSION}
    sudo ./configure --enable-optimizations  > ${TERM} 2>&1
    sudo make altinstall  > ${TERM} 2>&1
    sudo rm -f /opt/Python-{$PYTHON_VERSION}.tgz
    pip${PYTHON_MAJOR_VERSION} install --upgrade pip  > ${TERM} 2>&1

    echo "Making this version of python as default"
    sudo rm /usr/bin/python3
    sudo ln -s /usr/local/bin/python${PYTHON_MAJOR_VERSION} /usr/bin/python3 
}

function install_c9()
{
    print_line
    echo "Installing c9 executable"
    npm install -g c9
    print_line
}


function check_installation()
{
    overall="True"
    #Checking postgresql 
    psql -c "select version()" | grep PostgreSQL > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        echo "PostgreSQL installation successful : OK"
    else
        echo "PostgreSQL installation FAILED : NOTOK"
	overall="False"
    fi
    
    # Checking clone
    if [ -d ${HOME}/environment/${PROJ_NAME}/ ] ; then 
        echo "Git Clone successful : OK"
    else
        echo "Git Clone FAILED : NOTOK"
	overall="False"
    fi
   
    # Checking c9
    
    c9 --version > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        echo "C9 installation successful : OK"
    else
        echo "C9 installation FAILED : NOTOK"
	overall="False"
    fi

    # Checking python
    /usr/local/bin/python${PYTHON_MAJOR_VERSION} --version | grep Python  > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        echo "Python installation successful : OK"
    else
        echo "Python installation FAILED : NOTOK"
	overall="False"
    fi

    # Checking python3
    python3 --version | grep ${PYTHON_VERSION}  > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        echo "Python default installation successful : OK"
    else
        echo "Python default installation FAILED : NOTOK"
	overall="False"
    fi


    echo "=================================="
    if [ ${overall} == "True" ] ; then
        echo "Overall status : OK"
    else
        echo "Overall status : FAILED"
    fi
    echo "=================================="

}


function cp_logfile()
{

    bucket_name="genai-pgv-labs-${AWS_ACCOUNT_ID}-`date +%s`"
    echo ${bucket_name}
    aws s3 ls | grep ${bucket_name} > /dev/null 2>&1
    if [ $? -ne 0 ] ; then
        aws s3 mb s3://${bucket_name} --region ${AWS_REGION}
    fi

    aws s3 cp ${HOME}/environment/prereq.log s3://${bucket_name}/prereq_${AWS_ACCOUNT_ID}.txt > /dev/null 
    if [ $? -eq 0 ] ; then
	echo "Copied the logfile to bucket ${bucket_name}"
    else
	echo "Failed to copy logfile to bucket ${bucket_name}"
    fi
}
# Main program starts here

if [ ${1}X == "-xX" ] ; then
    TERM="/dev/tty"
else
    TERM="/dev/null"
fi

echo "Process started at `date`"
install_packages

export AWS_REGION=`curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | jq .region -r`
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text) 
 
install_postgresql
clone_git
configure_pg
install_extension
print_line
install_c9
print_line
install_python3
print_line
check_installation
cp_logfile

echo "Process completed at `date`"
