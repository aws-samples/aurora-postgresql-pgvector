import json
import boto3
import time
import logging
from botocore.exceptions import ClientError
from botocore.client import Config
import os
from datetime import datetime

# Define FM to be used for generations 
kb_id = os.getenv('KBID')
region_name = os.getenv('AWS_DEFAULT_REGION')
sts_client = boto3.client('sts')
boto3_session = boto3.session.Session()
model_id = "anthropic.claude-3-haiku-20240307-v1:0" # we will be using Anthropic Claude 3 Haiku throughout the notebook
model_arn = f'arn:aws:bedrock:{region_name}::foundation-model/{model_id}'

bedrock_config = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0}, region_name=region_name)
bedrock_agent_client = boto3_session.client("bedrock-agent-runtime", config=bedrock_config)


# Stating the default knowledge base prompt

default_prompt = """
You are a PostreSQL Database Administrator and your primary job is to analyze the incident reported and take any remedial actions.
You will receive the alerts or incidents as a tasks and you will carry the root cause analysis.
As a first step in the analysis, you will search the knowledge base for any available runbook for instructions.
The knowledge base provides the runbook which contains the step by step instructions to remedie the alert generated.
If you don't find the proper instructions from the knowledge base, end the conversation by saying "I couldn't find the runbook" and end the response.
You retrieve the instructions from the knowledge base and execute the steps in the knowlege base one at a time using the proper functions/tooling.
Strictly follow the instructions in the runbook and don't execute any other steps on your own. 
Stictly use only the functions required to carry out the operations in the proper order provided by the knowledge base instructions.
Finally summarize the actions you have taken.
                            
Here are the search results in numbered order:
$search_results$

$output_format_instructions$
"""

def retrieve_and_generate(query, max_results, prompt_template=default_prompt):
    response = bedrock_agent_client.retrieve_and_generate(
            input={
                'text': query
            },
        retrieveAndGenerateConfiguration={
        'type': 'KNOWLEDGE_BASE',
        'knowledgeBaseConfiguration': {
            'knowledgeBaseId': kb_id,
            'modelArn': model_arn, 
            'retrievalConfiguration': {
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results # will fetch top N documents which closely match the query
                    }
                },
                'generationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': prompt_template
                        }
                    }
            }
        }
    )
    return response

def update_dynamodb(id, username, output):

    dynamodb = boto3.client('dynamodb')
    tableName = os.environ.get('CWALERTTABLE', 'cwalerttable_v2')
    key = {"pk": {'S': id}, 'sk': {'S': 'I' } }
    response = dynamodb.update_item(
        TableName = tableName,
        Key=key, 
        UpdateExpression = "set incidentRunbook = :incidentRunbook, lastUpdate = :lastUpdate, lastUpdateBy = :lastUpdateBy", 
        ExpressionAttributeValues={
            ":incidentRunbook": {'S': json.dumps(output) },
            ":lastUpdate": {'S' : datetime.now().strftime("%Y-%m-%d %H:%M:%S") }, 
            ":lastUpdateBy": {'S': username }
            }, 
        ReturnValues="UPDATED_NEW",
        )


def lambda_handler(event, context):
    print(event)
    try:
        query = event['queryStringParameters']['query']
        id = event['queryStringParameters']['id']
    except KeyError:
        return { 'statusCode': 500, 'body': json.dumps('No description found in the alarm') }
   
    username = event.get('requestContext',{}).get('authorizer',{}).get('claims', {}).get('email')

    print(f"Calling the function to execute the query : {query}")    
    response = retrieve_and_generate(query = query, max_results = 1)
    generated_text = response['output']['text']
    output = {"runbook": generated_text}
    
    update_dynamodb(id, username, output)
    print('Generated FM response:\n')
    print(generated_text)
    return {
        'statusCode': '200',
        'body': json.dumps(output),
        'headers': {
            'Content-Type': 'application/json',
        }
    }


