import os
import boto3

boto3_session = boto3.session.Session()
region = boto3_session.region_name

# create a boto3 bedrock client
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

# Cross-region inference profile; override via BEDROCK_MODEL_ID env var
# global.anthropic.claude-sonnet-5 is also available as an override
model_id = os.environ.get('BEDROCK_MODEL_ID', 'global.anthropic.claude-sonnet-5')
kb_id = os.environ.get('KBID')
if not kb_id:
    raise RuntimeError("KBID environment variable is required but not set.")

# Cross-region inference profiles (us./eu./ap./global. prefix) use inference-profile ARN type
model_arn = (
    f'arn:aws:bedrock:{region}::inference-profile/{model_id}'
    if model_id.startswith(('us.', 'eu.', 'ap.', 'global.'))
    else f'arn:aws:bedrock:{region}::foundation-model/{model_id}'
)

def retrieveAndGenerate(input, kbId, model_arn, sessionId):
    print(input, kbId, model_arn, sessionId)
    if sessionId != "":
        return bedrock_agent_runtime_client.retrieve_and_generate(
            input={
                'text': input
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kbId,
                    'modelArn': model_arn
                }
            },
            sessionId=sessionId
        )
    else:
        return bedrock_agent_runtime_client.retrieve_and_generate(
            input={
                'text': input
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kbId,
                    'modelArn': model_arn
                }
            }
        )
        
def lambda_handler(event, context):
    print (event)
    query = event["alert"]
    sessionId = event["sessionId"]
    response = retrieveAndGenerate(query, kb_id, model_arn, '')
    # response = retrieveAndGenerate(query, kb_id, model_arn, sessionId)
    generated_text = response['output']['text']
    print(generated_text)
    sessionId = response['sessionId']
    citations = response['citations']
    return {
        'statusCode': 200,
        'body': {"question": query.strip(), "answer": generated_text.strip(), "sessionId":sessionId, "citations":citations}
    }

