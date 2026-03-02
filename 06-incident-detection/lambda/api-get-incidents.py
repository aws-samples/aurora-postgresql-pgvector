import json
import boto3
from boto3.dynamodb.conditions import Attr
import os

def lambda_handler(event, context):
    print (event)
    incidentStatus = None
    try:
        incidentStatus = event['queryStringParameters']['incidentStatus']
    except KeyError:
        return { 'statusCode': 500, 'body': json.dumps('No status found in the alarm') }
        
    # Initialize the DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    
    tableName = os.getenv('CWALERTTABLE')
    table  = dynamodb.Table(tableName)
    
    print(f"Getting the DynamoDB table {tableName}  content for incidentStatus {incidentStatus}")

    # Getting the incidents for the sort key ("I")

    if incidentStatus == "all":
        response = table.scan(
            FilterExpression=Attr('sk').eq('I')
        )
    else:
        response = table.scan(
            FilterExpression=Attr('incidentStatus').eq(incidentStatus) & Attr('sk').eq('I')
        )
    print (response)
    return {
        'statusCode': '200',
        'body': json.dumps(response),
        'headers': {
            'Content-Type': 'application/json',
        }
    }
