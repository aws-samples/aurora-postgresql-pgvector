#!/bin/bash
#
export PROJ_NAME="DAT307"
export BASEDIR=${HOME}/environment/${PROJ_NAME}
export AWS_PAGER=""

function install_lambda()
{
    lambda="idr-bedrock-agent-action-group"
    rm -rf /tmp/${lambda}
    mkdir /tmp/${lambda}
    cp ${BASEDIR}/lambda/${lambda}-good.py /tmp/${lambda}/index.py
    cd /tmp/${lambda}
    zip -r ${lambda}.zip index.py
    aws lambda update-function-code --function-name  ${lambda}  --zip-file fileb:///tmp/${lambda}/${lambda}.zip
    if [ $? -eq 0 ] ; then
        echo "Deployed the lambda function successfully"
    else
        echo "ERROR !!!! Failed to deploye the lambda function"
    fi
}

install_lambda
