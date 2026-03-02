#!/bin/bash


export PROJ_NAME="DAT307"
#export GITHUB_URL="https://github.com/aws-samples/"
export GITHUB_NAME="aurora-postgresql-pgvector"
export GITHUB_URL="https://github.com/ajrajkumar/"
export PYTHON_MAJOR_VERSION="3.12"
export PYTHON_MINOR_VERSION="1"
export PYTHON_VERSION="${PYTHON_MAJOR_VERSION}.${PYTHON_MINOR_VERSION}"
export PGVERSION="16.3"
export BASEDIR=${HOME}/environment/${PROJ_NAME}
export AWS_PAGER=""
export TEMP_DIR=/tmp
export USERNAME=demo@dat307.com
export PASSWORD=Welcome@reInvent2024

function check_cfn_status()
{
    typeset -i counter
    counter=0
    echo "Checking if the cloudformation completed successfully at `date`"

    while [ $counter -lt 30 ]
    do
        counter=$counter+1
        KB_IDR_S3=$(aws cloudformation describe-stacks --query "Stacks[].Outputs[?(OutputKey == 'KBIDRS3SourceBucketName')][].{OutputValue:OutputValue}" --output text)
	if [ "${KB_IDR_S3}" == "" ] ; then
            echo "The cloudformation is not yet complete.. sleeping for 30 sec -- loop ${counter} at `date`"
        else
            echo "The cloudformation completeted successfully - ${KB__IDR_S3} at `date`"
	    break
	fi
	sleep 30
    done

}

function print_line()
{
    echo "---------------------------------"
}

function install_packages()
{
    sudo yum install -y jq  > ${TERM} 2>&1
    print_line
    echo "Increasing the storage size"
    source <(curl -s https://raw.githubusercontent.com/aws-samples/aws-swb-cloud9-init/mainline/cloud9-resize.sh)
    echo "Installing aws cli v2"
    print_line
    aws --version | grep aws-cli\/2 > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        cd $current_dir
	return
    fi
    current_dir=`pwd`
    cd ${TEMP_DIR}
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
    sudo yum install -y readline-devel zlib-devel gcc
    if [ ! -f /usr/local/pgsql/bin/psql ] ; then
        cd ${TEMP_DIR}
        wget https://ftp.postgresql.org/pub/source/v${PGVERSION}/postgresql-${PGVERSION}.tar.gz > ${TERM} 2>&1
        tar -xvf postgresql-${PGVERSION}.tar.gz > ${TERM} 2>&1
        cd postgresql-${PGVERSION}
        ./configure --without-icu > ${TERM} 2>&1
        make > ${TERM} 2>&1
        sudo make install > ${TERM} 2>&1
    else
	echo "PostgreSQL already installed.. skipping"
    fi

    sudo amazon-linux-extras install -y postgresql14 > ${TERM} 2>&1
    sudo yum install -y postgresql-contrib sysbench > ${TERM} 2>&1

}

function clone_git()
{
    print_line
    echo "Cloning the git repository"
    print_line
    cd ${HOME}/environment
    rm -rf ${PROJ_NAME}
    git clone ${GITHUB_URL}${GITHUB_NAME}
    mv ${GITHUB_NAME}/${PROJ_NAME} ${HOME}/environment
    rm -rf ${GITHUB_NAME}
    cd ${PROJ_NAME}
    print_line
}


function configure_env()
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

    export APIGWURL=$(aws cloudformation describe-stacks --query "Stacks[].Outputs[?(OutputKey == 'APIGatewayURL')][].{OutputValue:OutputValue}" --output text)
    export APIGWSTAGE=$(aws cloudformation describe-stacks --query "Stacks[].Outputs[?(OutputKey == 'APIGatewayStage')][].{OutputValue:OutputValue}" --output text)
    export APP_CLIENT_ID=$(aws cloudformation describe-stacks --query "Stacks[].Outputs[?(OutputKey == 'CognitoClientID')][].{OutputValue:OutputValue}" --output text)

    export KB_IDR_S3=$(aws cloudformation describe-stacks --query "Stacks[].Outputs[?(OutputKey == 'KBIDRS3SourceBucketName')][].{OutputValue:OutputValue}" --output text)
    export KB_QA_S3=$(aws cloudformation describe-stacks --query "Stacks[].Outputs[?(OutputKey == 'KBQAS3SourceBucketName')][].{OutputValue:OutputValue}" --output text)

    export S3_LINK_URL=$(aws cloudformation describe-stacks --query "Stacks[].Outputs[?(OutputKey == 'S3LinkUrl')][].{OutputValue:OutputValue}" --output text)

    export C9_URL="https://\${C9_PID}.vfs.cloud9.${AWS_REGION}.amazonaws.com/"


    # Persist values in future terminals
    echo "export PGUSER=$PGUSER" >> /home/ec2-user/.bashrc
    echo "export PGPASSWORD='$PGPASSWORD'" >> /home/ec2-user/.bashrc
    echo "export PGHOST=$PGHOST" >> /home/ec2-user/.bashrc
    echo "export AWS_REGION=$AWS_REGION" >> /home/ec2-user/.bashrc
    echo "export AWSREGION=$AWS_REGION" >> /home/ec2-user/.bashrc
    echo "export PGDATABASE=postgres" >> /home/ec2-user/.bashrc
    echo "export PGPORT=5432" >> /home/ec2-user/.bashrc
    echo "export PATH=/usr/local/pgsql/bin:\${PATH}" >> /home/ec2-user/.bashrc
    echo "export APIGWURL=${APIGWURL}" >> /home/ec2-user/.bashrc
    echo "export APIGWSTAGE=${APIGWSTAGE}" >> /home/ec2-user/.bashrc
    echo "export APP_CLIENT_ID=${APP_CLIENT_ID}" >> /home/ec2-user/.bashrc
    echo "export C9_URL=${C9_URL}" >> /home/ec2-user/.bashrc
    echo "export KB_IDR_S3=${KB_IDR_S3}" >> /home/ec2-user/.bashrc
    echo "export KB_QA_S3=${KB_QA_S3}" >> /home/ec2-user/.bashrc
    echo "export S3_LINK_URL=${S3_LINK_URL}" >> /home/ec2-user/.bashrc
}

function install_extension()
{
    psql -h ${PGHOST} -c "create extension if not exists vector"
}


function load_table()
{
    DUMP_SQL=dump.sql
    cp ${BASEDIR}/data/${DUMP_SQL}.gz ${TEMP_DIR}
    gunzip ${TEMP_DIR}/${DUMP_SQL}.gz
    psql -h ${PGHOST} < ${TEMP_DIR}/${DUMP_SQL}
    rm ${TEMP_DIR}/${DUMP_SQL}

}

function initialize_pgbench()
{

    OUTPUT=$(aws secretsmanager get-secret-value --secret-id rdspg-idr-iops-secret --query SecretString --output text)
    host=`echo ${OUTPUT} | jq -r '.host'`
    password=`echo ${OUTPUT} | jq -r '.password'`
    username=`echo ${OUTPUT} | jq -r '.username'`
    PGPASSWORD=${password} /usr/local/pgsql/bin/pgbench -i -n -s 200 -h ${host} -U postgres -d postgres -p 5432
}


function streamlit_requirements()
{
    cd ~/environment/DAT307/ui
    pip3.12 install -r requirements.txt > ${TERM} 2>&1
}

function install_python3()
{
    # Install Python 3
    sudo yum remove -y openssl-devel > ${TERM} 2>&1
    sudo yum install -y gcc openssl11-devel bzip2-devel libffi-devel sqlite-devel > ${TERM} 2>&1

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

    # Installing required modules
    
    pip${PYTHON_MAJOR_VERSION} install boto3 psycopg2-binary requests  > ${TERM} 2>&1

    echo "Making this version of python as default"
    sudo rm /usr/bin/python3
    sudo ln -s /usr/local/bin/python${PYTHON_MAJOR_VERSION} /usr/bin/python3 
}

function install_c9()
{
    print_line
    echo "Installing c9 executable"
    sudo npm install -g c9
    print_line
}


function check_installation()
{
    overall="True"
    #Checking postgresql 
    psql -c "select version()" | grep PostgreSQL > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        echo "PostgreSQL installation successful : SUCCESS"
    else
        echo "PostgreSQL installation FAILED : FAILED"
	overall="False"
    fi
    
    # Checking clone
    if [ -d ${HOME}/environment/${PROJ_NAME}/ ] ; then 
        echo "Git Clone successful : SUCCESS"
    else
        echo "Git Clone FAILED : FAILED"
	overall="False"
    fi
   
    # Checking c9
    
    c9 --version > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        echo "C9 installation successful : SUCCESS"
    else
        echo "C9 installation FAILED : FAILED"
	overall="False"
    fi

    #Checking streamlit
    streamlit --version > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        echo "streamlit installation successful : SUCCESS"
    else
        echo "streamlit installation FAILED : FAILED"
	overall="False"
    fi

    # Checking python
    /usr/local/bin/python${PYTHON_MAJOR_VERSION} --version | grep Python  > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        echo "Python installation successful : SUCCESS"
    else
        echo "Python installation FAILED : FAILED"
	overall="False"
    fi

    # Checking python3
    python3 --version | grep ${PYTHON_VERSION}  > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        echo "Python default installation successful : SUCCESS"
    else
        echo "Python default installation FAILED : FAILED"
	overall="False"
    fi

    # Checking if variables have proper values
    for var in APIGWURL APIGWSTAGE APP_CLIENT_ID KB_IDR_S3 KB_QA_S3 S3_LINK_URL
    do
        if [ ${!var} == "" ] ; then
            echo "${var} is not set propertly : FAILED"
	    overall="False"
	else
            echo "${var} is set propertly : SUCCESS"
        fi     
    done

    # Checking cognito user creation
    export COGNITO_CLIENT_ID=$(aws cloudformation describe-stacks --query "Stacks[].Outputs[?(OutputKey == 'CognitoClientID')][].{OutputValue:OutputValue}" --output text)
    aws cognito-idp initiate-auth --client-id ${COGNITO_CLIENT_ID} --auth-flow USER_PASSWORD_AUTH --auth-parameters USERNAME=${USERNAME},PASSWORD=${PASSWORD} > /dev/null

    if [ ${?} -eq 0 ] ; then
        echo "Username created successfully in cognito: SUCCESS"
    else
        echo "Failed to create username in cognito : FAILED"
	overall="False"
    fi

    echo "=================================="
    if [ ${overall} == "True" ] ; then
        echo "OVERALL status : SUCCESS"
    else
        echo "OVERALL status : FAILED"
    fi
    echo "=================================="

}

function install_lambda()
{

    for lambda in cw-ingest-to-dynamodb idr-bedrock-agent-action-group qa-bedrock-agent-action-group api-get-incidents api-list-runbook-kb api-action-runbook-kb
    do
        rm -rf ${TEMP_DIR}/${lambda}
        mkdir ${TEMP_DIR}/${lambda}
        cp ${BASEDIR}/lambda/${lambda}.py ${TEMP_DIR}/${lambda}/index.py
        cd ${TEMP_DIR}/${lambda}
        zip -r ${lambda}.zip index.py
        aws lambda update-function-code --function-name  ${lambda}  --zip-file fileb://${TEMP_DIR}/${lambda}/${lambda}.zip
    done

}


function create_user()
{
    echo "Creating cognito demo user"
    export COGNITO_USER_POOL_ID=$(aws cloudformation describe-stacks --query "Stacks[].Outputs[?(OutputKey == 'CognitoUserpoolID')][].{OutputValue:OutputValue}" --output text)

    aws cognito-idp admin-create-user --user-pool-id ${COGNITO_USER_POOL_ID} --username ${USERNAME} --user-attributes Name=email,Value=${USERNAME} --message-action SUPPRESS  > /dev/null
    aws cognito-idp admin-set-user-password --user-pool-id ${COGNITO_USER_POOL_ID} --username ${USERNAME} --password ${PASSWORD} --permanent  > /dev/null

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

    END_TIME=`date +%s`
    TOTAL_TIME=`expr ${END_TIME} - ${START_TIME}`
    echo "TOTAL_TIME_TAKEN : ${TOTAL_TIME} sec"

    echo "Process completed at `date`"

    # Copying the logfile for review
    curl --request PUT "${S3_LINK_URL}${AWS_ACCOUNT_ID}_prereq.txt" --header 'Content-Type: text/plain' --data-binary "@${HOME}/environment/prereq.log"
}

# Main program starts here

if [ ${1}X == "-xX" ] ; then
    TERM="/dev/tty"
else
    TERM="/dev/null"
fi

echo "Process started at `date`"
START_TIME=`date +%s`
check_cfn_status
install_packages

export AWS_REGION=`curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | jq .region -r`
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text) 

install_postgresql
clone_git
configure_env
install_extension
print_line
install_c9
print_line
install_python3
print_line
install_lambda
print_line
create_user
print_line
load_table
#print_line
# Commenting out the pgbench as it causes the IOPS alert
#initialize_pgbench
print_line
streamlit_requirements
print_line
check_installation
print_line
cp_logfile

echo "Process completed at `date`"
