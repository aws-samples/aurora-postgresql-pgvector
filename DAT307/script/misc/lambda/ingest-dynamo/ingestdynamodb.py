import json
import logging
import os
import boto3
import uuid
from datetime import datetime

def lambda_handler(event, context):
    # TODO implement
    print (event)
    print (context)
    dynamodb = boto3.client('dynamodb')
    tableName = os.environ.get('CWALERTTABLE', 'cwalerttable_v2')
    metricStat = {}

    item = {'pk':{'S': uuid.uuid4().hex }, 'sk': {'S': 'A'},
            'SessionStatus':{'S': 'A'},
            'incidentData': {'S': event},
            'incidentActionTrace': {'S', 'None'},
            'lastUpdate': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'lastUpdateBy': event.get('source', 'aws.cloudwatch')
            }
    response = dynamodb.put_item(TableName=tableName, Item=item)

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
