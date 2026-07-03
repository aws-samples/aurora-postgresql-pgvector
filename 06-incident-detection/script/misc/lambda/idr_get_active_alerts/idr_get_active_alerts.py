import json
import boto3
from boto3.dynamodb.conditions import Attr
import os
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def lambda_handler(event, context):
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
        'body': json.dumps(response.get('Items', []), cls=DecimalEncoder)
    }
