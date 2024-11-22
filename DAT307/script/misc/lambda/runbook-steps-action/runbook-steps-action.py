import os
import boto3
import time
import json

boto3_session = boto3.session.Session()
region = boto3_session.region_name

# create a boto3 bedrock client
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

agent_id = os.environ.get('AGENTID', '2EOQS4ZE93')
agent_alias_id = os.environ.get('AGENTALIASID', '135OAPMTED')
dynamodb = boto3.client('dynamodb')
tableName = os.environ.get('CWALERTTABLE', 'cwalerttable_v2')
table = dynamodb.Table(tableName)

def lambda_handler(event, context):
    print (event)
    inputText = event["inputText"]
    sessionId = event["sessionId"]
    sessionType = event['sessionType']
    DBInstanceIdentifier= event["DBInstanceIdentifier"]
    alertType = event["alertType"]
    username = event.get('requestContext',{}).get('authorizer',{}).get('claims', {}).get('email')
    
    if sessionId != "":
        response = bedrock_agent_runtime_client.invoke_agent(
            inputText=inputText,
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=sessionId,
            enableTrace=True,
            endSession=False
           )
    else:
        response = bedrock_agent_runtime_client.invoke_agent(
            inputText=inputText,
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=sessionId,
            enableTrace=True,
            endSession=False
           )
    event_stream = response['completion']
    agent_answer = {"status": "Action completed successfully"}
    print (response)
    time.sleep (10)
    for event in event_stream:
        print (event)
        if 'chunk' in event:
            data = event['chunk']['bytes']
            print (f"Final answer ->\n{data.decode('utf8')}")
            agent_answer = data.decode('utf8')
            end_event_received = True
        elif 'trace' in event:
            agent_trace = json.dumps(event['trace'], indent=2)

    key = {"pk": {'S': sessionId}, 'sk': {'S': sessionType } }
    response = table.update_item(Key=key, UpdateExpression = "set SessionStatus = :SessionStatus, incidentActionTrace = :incidentActionTrace, incidentActionResponse = :incidentActionResponse, lastUpdate = :lastUpdate, lastUpdateBy = :lastUpdateBy", ExpressionAttributeValues={":SessionStatus": 'R', ":incidentActionTrace": agent_trace, ":incidentActionResponse": agent_answer, ":lastUpdate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ":lastUpdateBy": username)}, ReturnValues="UPDATED_NEW", )

    return {
        'statusCode': 200,
        'body': json.dumps(agent_answer)
    }
