import json
import boto3
import json
import time
import zipfile
from io import BytesIO
import uuid
import pprint
import logging

logger = logging.getLogger()
logger.setLevel("INFO")


def simple_agent_invoke(input_text):
    bedrock_agent_client = boto3.client('bedrock-agent')
    bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

    session_id:str = str(uuid.uuid1())
    agent_id = "2EOQS4ZE93"
    agent_alias_id = "TSTALIASID"    
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
        for event in event_stream:        
            if 'chunk' in event:
                data = event['chunk']['bytes']
                logger.info(f"Final answer ->\n{data.decode('utf8')}")
                agent_answer = data.decode('utf8')
                end_event_received = True
                # End event indicates that the request finished successfully
            elif 'trace' in event:
                a = event['trace']
                try:
                    a['trace']['preProcessingTrace']['modelInvocationInput']['text'] = "TEXT"
                except KeyError:
                    pass          
                try:
                    a['trace']['orchestrationTrace']['modelInvocationInput']['text'] = "TEXT"
                except KeyError:
                    pass
                logger.info(json.dumps(a, indent=2))
                logger.info("\n=====================================================================================\n")
            else:
                raise Exception("unexpected event.", event)
    except Exception as e:
        raise Exception("unexpected event.", e)

def lambda_handler(event, context):
    logger.info(event)
    try:
        action = event['alarmData']['configuration']['description']
    except KeyError:
        return { 'statusCode': 500, 'body': json.dumps('No description found in the alarm') }
    logger.info(f"Calling the function to execute the query : {action}")    
    simple_agent_invoke(action)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
