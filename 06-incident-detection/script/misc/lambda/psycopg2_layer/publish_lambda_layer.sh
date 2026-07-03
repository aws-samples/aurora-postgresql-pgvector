#!/bin/bash

aws lambda publish-layer-version --layer-name psycopg2-layer \
    --description "Psycopg2 PostgreSQL Client Library Layer" \
    --license-info "MIT" \
    --zip-file fileb://psycopg2.zip \
    --compatible-runtimes python3.12 \
    --compatible-architectures "x86_64"
