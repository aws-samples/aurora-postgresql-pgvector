import json
import boto3
import json
import time
import zipfile
from io import BytesIO
import uuid
import pprint
import logging
import os
from datetime import datetime

boto3_session = boto3.session.Session()
region = boto3_session.region_name

agent_id = os.environ.get('AGENTID')
agent_alias_id = 'TSTALIASID'

logger = logging.getLogger()
logger.setLevel("INFO")


def simple_agent_invoke(input_text):
    bedrock_agent_client = boto3.client('bedrock-agent')
    bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

    session_id:str = str(uuid.uuid1())
    agentResponse = bedrock_agent_runtime_client.invoke_agent(
        inputText=input_text,
        agentId=agent_id,
        agentAliasId=agent_alias_id, 
        sessionId=session_id,
        enableTrace=True, 
        endSession= False
    )
    logger.info(pprint.pprint(agentResponse))
    
    event_stream = agentResponse['completion']
    try:
        output = []
        for event in event_stream:        
            if 'chunk' in event:
                data = event['chunk']['bytes']
                logger.info(f"Final answer ->\n{data.decode('utf8')}")
                agent_answer = data.decode('utf8')
                end_event_received = True
                # End event indicates that the request finished successfully
            elif 'trace' in event:
                a = event['trace']
                log_data = True
                try:
                    dummy = a['trace']['orchestrationTrace']['rationale']
                except KeyError:
                    try:
                        dummy = a['trace']['orchestrationTrace']['observation']
                    except KeyError:
                        try:
                            dummy = a['trace']['orchestrationTrace']['invocationInput']
                        except KeyError:
                            log_data = False
                            
                if log_data:
                    logger.info(json.dumps(a['trace'], indent=2))
                    output.append(a['trace'])
                    logger.info("\n=====================================================================================\n")
            else:
                raise Exception("unexpected event.", event)
        return output 
    except Exception as e:
        raise Exception("unexpected event.", e)

def update_dynamodb(id, username, result):

    dynamodb = boto3.client('dynamodb')
    tableName = os.environ.get('CWALERTTABLE', 'cwalerttable_v2')
    key = {"pk": {'S': id}, 'sk': {'S': 'I' } }
    response = dynamodb.update_item(
        TableName = tableName,
        Key=key, 
        UpdateExpression = "set incidentActionTrace = :incidentActionTrace, lastUpdate = :lastUpdate, lastUpdateBy = :lastUpdateBy, incidentStatus = :incidentStatus", 
        ExpressionAttributeValues={
            ":incidentActionTrace": {'S': json.dumps(result) },
            ":incidentStatus": {'S': 'completed'},
            ":lastUpdate": {'S' : datetime.now().strftime("%Y-%m-%d %H:%M:%S") }, 
            ":lastUpdateBy": {'S': username }
            }, 
        ReturnValues="UPDATED_NEW",
        )

def lambda_handler(event, context):
    logger.info(event)
    try:
        action = json.loads(event['body'])['action']
        id = json.loads(event['body'])['id']
    except KeyError:
        return { 'statusCode': 500, 'body': json.dumps('No description found in the alarm') }
    logger.info(f"Calling the function to execute the query : {action}")    
    username = event.get('requestContext',{}).get('authorizer',{}).get('claims', {}).get('email')
    output = simple_agent_invoke(action)
    result = {"result":output}
    update_dynamodb(id, username, result)

    return {
        'statusCode': '200',
        'body': json.dumps(result),
        'headers': {
            'Content-Type': 'application/json',
        }
    }   
    


