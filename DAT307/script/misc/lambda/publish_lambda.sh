#!/bin/bash

LayerARN=`aws lambda publish-layer-version --layer-name psycopg2-layer \
    --description "Psycopg2 PostgreSQL Client Library Layer" \
    --license-info "MIT" \
    --zip-file fileb://psycopg2_layer/psycopg2.zip \
    --compatible-runtimes python3.9 \
    --compatible-architectures "x86_64" | jq .LayerArn`

if [[ $? -ne 0 ]]; then
        echo "ERROR: Failed to create Psycopg2 Layer, Please review below error and fix it"
        echo $LayerARN
        exit 1
fi

AcctID=`echo $LayerARN | awk -F: '{print $5}'`
Regn=`echo $LayerARN | awk -F: '{print $4}'`

aws ecr create-repository --repository-name dat307-s3-upload

#s3upload

docker buildx build --platform linux/amd64 -t ${AcctID}.dkr.ecr.${Regn}.amazonaws.com/dat307-s3-upload:1.0 s3upload/.
aws ecr get-login-password --region ${Regn} | docker login --username AWS --password-stdin ${AcctID}.dkr.ecr.${Regn}.amazonaws.com/dat307-s3-upload
docker push ${AcctID}.dkr.ecr.${Regn}.amazonaws.com/dat307-s3-upload:1.0
if [[ $? -ne 0 ]]; then
        echo "ERROR: Failed to create s3-upload image, Please review above error and fix it"
        exit 1
fi

