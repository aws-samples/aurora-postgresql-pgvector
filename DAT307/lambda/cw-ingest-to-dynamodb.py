import json
import logging
import os
import boto3
import uuid
import datetime

def lambda_handler(event, context):
    print (event)

    dynamodb = boto3.client('dynamodb')
    tableName = os.getenv('CWALERTTABLE')
    
    incidentType = None
    incidentIdentifier = None
    
    try:
        incidentType = event.get('alarmData').get('configuration').get('metrics')[0]['label']
    except:
        incidentType = event.get('alarmData').get('configuration').get('metrics')[0].get('metricStat').get('metric').get('name')
    
    for metric in event.get('alarmData').get('configuration').get('metrics'):
        try:
            incidentIdentifier = metric['metricStat']['metric']['dimensions']['DBInstanceIdentifier']
        except:
            try:
                incidentIdentifier = metric['metricStat']['metric']['dimensions']['DBClusterIdentifier']
            except:
                incidentIdentifier = "N/A"
    item = {
            'pk': {'S': uuid.uuid4().hex }, 
            'sk': {'S': 'I'},
            'incidentStatus': {'S': 'pending'},
            'incidentData': {'S': json.dumps(event.get('alarmData'))},
            'incidentRunbook': {'S': 'None'},
            'incidentActionTrace': {'S': 'None'},
            'incidentTime': {'S': event.get('time')},
            'lastUpdate': {'S': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            'lastUpdateBy': {'S': event.get('source', 'aws.cloudwatch')},
            'incidentType' : {'S': incidentType},
            'incidentIdentifier': {'S': incidentIdentifier}
        }
        
    response = dynamodb.put_item(TableName=tableName, Item=item)

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
