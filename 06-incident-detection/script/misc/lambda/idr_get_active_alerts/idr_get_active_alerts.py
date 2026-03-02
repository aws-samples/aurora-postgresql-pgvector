import json
import boto3
from boto3.dynamodb.conditions import Attr
import os

def lambda_handler(event, context):
    # TODO implement
    print (event)
    print (context)
    
    # Initialize the DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    tableName = os.environ.get('CWALERTTABLE', 'cwalerttable_v2')
    table = dynamodb.Table(tableName)

    # Scan the table and filter based on sort key sk -> # SessionType: A - Incident Alert, M - User Conversation Only
    response = table.scan(
        FilterExpression=Attr('sk').ne('D')
    )
    print (response)
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }

