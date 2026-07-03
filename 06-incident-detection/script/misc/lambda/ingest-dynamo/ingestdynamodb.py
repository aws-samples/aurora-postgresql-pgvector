import json
import logging
import os
import boto3
import uuid
from datetime import datetime

def lambda_handler(event, context):
    print (event)
    print (context)
    dynamodb = boto3.resource('dynamodb')
    tableName = os.environ.get('CWALERTTABLE', 'cwalerttable_v2')
    table = dynamodb.Table(tableName)

    item = {
        'pk': uuid.uuid4().hex,
        'sk': 'A',
        'SessionStatus': 'A',
        'incidentData': json.dumps(event),
        'incidentActionTrace': 'None',
        'lastUpdate': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'lastUpdateBy': event.get('source') or 'aws.cloudwatch',
    }
    table.put_item(Item=item)

    return {
        'statusCode': 200,
        'body': json.dumps({'pk': item['pk'], 'sk': item['sk']})
    }
