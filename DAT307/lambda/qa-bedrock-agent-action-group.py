import json
import os
import boto3
import logging
import traceback
from botocore.client import Config
import datetime
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Attr

config = Config(connect_timeout=5, retries={'max_attempts': 0})

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
lambda_logger = logging.getLogger(__name__)

if lambda_logger.hasHandlers():
    lambda_logger.setLevel(LOG_LEVEL)
else:
    logging.basicConfig(level=LOG_LEVEL)

region_name = os.environ['AWS_REGION']

rdsClient = boto3.client('rds',region_name=region_name,config=config)
cloudwatchClient = boto3.client('cloudwatch', region_name=region_name,config=config)


#==============================================================================================================================            
# Helper functions

def get_param(parameters, parameter, mandatory=True):
    param_value = None
    for param in parameters:
        if param["name"] == parameter:
            param_value = param["value"]
    if not param_value and mandatory:
            raise Exception("Missing mandatory parameter: {}".format(parameter))        
    return param_value
    
def build_api_response(event, status_code, response_message):
    """
    Helper function to build the structured API response.
    TODO: can be abstracted as a lib
    """
    responseBody =  { "TEXT": {"body": response_message} }   
    
    action_response = {
        'actionGroup': event['actionGroup'],
        'function': event['function'],
        'functionResponse': {
            'responseBody': responseBody
        }
        
    }

    api_response = {'response': action_response, 'messageVersion': event['messageVersion']}

    return api_response

def get_cluster_details_helper(dbClusterName):
    try:
        response = rdsClient.describe_db_clusters(DBClusterIdentifier=dbClusterName)
        return response['DBClusters'][0]
    except Exception as e:
        lambda_logger.error(f"Unable to get the instance details: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"
        
def get_cluster_name(db_instance_identifier):
    try:
        response = get_instance_details_helper(db_instance_identifier)
        dbClusterName =  response['DBClusterIdentifier']
        return dbClusterName
    except Exception as e:
        lambda_logger.error(f"Unable to get the cluster identifier details: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"


#==============================================================================================================================            
    
# Action group functions

def gather_infra():
    """
      Function to retrieve the instance details of RDS Cluster. Output will be in json format 
    """
    try:
        response = rdsClient.describe_db_instances()
        output = []
        
        for instance in response['DBInstances']:
            if instance['DBParameterGroups'][0]['ParameterApplyStatus'] == 'pending-reboot':
                pending_reboot = True
            else:
                pending_reboot = False
            output.append(
                {
                    "DBInstanceIdentifier" : instance['DBInstanceIdentifier'],
                    "Engine" : instance["Engine"],
                    "EngineVersion" : instance["EngineVersion"],
                    "PubliclyAccessible" : instance["PubliclyAccessible"],
                    "PendingReboot" : pending_reboot,
                    "MultiAZ" : instance["MultiAZ"]
                })
        return json.dumps(output, indent=2, sort_keys=True, default=str)
    except Exception as e:
        lambda_logger.error(f"Unable to get the instance details: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"

def gather_incidents():
    """
      Function to retrieve the incident details of RDS Cluster. Output will be in json format 
    """
    try:
        output = []
        dynamodb = boto3.resource('dynamodb')
        tableName = os.getenv('CWALERTTABLE')
        table  = dynamodb.Table(tableName)

        # Getting the incidents for the sort key ("I")
        response = table.scan(
            FilterExpression= Attr('sk').eq('I')
        )
        print(response)

        for item in response['Items']:
            output.append(
                {   "IncidentIdentifier" : item['incidentIdentifier'],
                    "IncidentType" : item['incidentType'],
                    "IncidentStatus" : item['incidentStatus'],
                    "ResolvedBy" : item['lastUpdateBy'],
                    "ResolvedAt" : item['lastUpdate'] })
        return json.dumps(output, indent=2, sort_keys=True, default=str)
    except Exception as e:
        lambda_logger.error(f"Unable to get the incident details: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"

def gather_metrics(db_instance_identifier, metric_name, metric_time, metric_stat=None):
    
    start_date =  datetime.utcnow() - timedelta(hours=int(metric_time))
    end_date = datetime.utcnow()
    period = int(metric_time)*60*60 
    metricQueries = None
    outText = None
    
    if metric_stat is None:
        metricStat = 'Maximum'
    elif 'max' in metric_stat.lower():
        metricStat = 'Maximum'
    elif 'min' in metric_stat.lower() :
        metricStat = 'Maximum'
    elif 'avg' in metric_stat.lower() or 'average' in metric_stat.lower():
        metricStat = 'Average'
    
    if 'cpu' in metric_name.lower() :
        outText = f"{metricStat} CPU utilization is"
        metricQueries = [
            {
                'Id': 'myrequest',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': 'CPUUtilization',
                        'Dimensions': [
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': db_instance_identifier
                            },
                        ]
                    },
                    'Period': period,
                    'Stat': metricStat
                }
            },
        ]
        
    if 'iops' in metric_name.lower() :
        outText =  f"{metricStat} IOPS utilization is"
        metricQueries = [
            {
                "Id": "e1",
                "Expression": "m1 + m2",
                "Label": "TotalIOPS"
            },
            {
                "Id": "m1",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/RDS",
                        "MetricName": "ReadIOPS",
                        'Dimensions': [
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': db_instance_identifier
                            },
                        ]
                    },
                    "Period": period,
                    "Stat": metricStat
                },
                "ReturnData": False
            },
            {
                "Id": "m2",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/RDS",
                        "MetricName": "WriteIOPS",
                        'Dimensions': [
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': db_instance_identifier
                            },
                        ]
                    },
                    "Period": period,
                    "Stat": metricStat
                },
                "ReturnData": False
            }
        ]
        
    if metric_name.lower() in 'acu':
        outText  =  f"{metricStat} ACU utilization is"
        metricQueries = [
            {
                'Id': 'myrequest',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': 'ServerlessDatabaseCapacity',
                        'Dimensions': [
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': db_instance_identifier
                            },
                        ]
                    },
                    'Period': period,
                    'Stat': metricStat
                }
            },
        ]
        

    response = cloudwatchClient.get_metric_data(
        MetricDataQueries=metricQueries,
        StartTime=start_date, 
        EndTime=end_date,    
    )
    metric_value = int(response["MetricDataResults"][0]['Values'][0])
    return f"{outText} {metric_value}"

#==============================================================================================================================            

def lambda_handler(event, context):
    try:
        lambda_logger.info(f"Received event: {event}")
 
        agent = event['agent']
        actionGroup = event['actionGroup']
        function = event['function']
        parameters = event.get('parameters', [])
        print(event)
        print(context)
        responseMessage = None
        
        
        if function == "gather_metrics":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            metric_name = get_param(parameters, "metric_name")
            metric_time = get_param(parameters, "metric_time")
            metric_stat = get_param(parameters, "metric_stat",False)
            responseMessage = gather_metrics(db_instance_identifier,metric_name,metric_time,metric_stat)

        if function == "gather_infra":
            responseMessage = gather_infra()
            
        if function == "gather_incidents":
            responseMessage = gather_incidents()

        lambda_logger.info(f"Response: {responseMessage}")
        return build_api_response(event, 200, str(responseMessage))

    except Exception as e:
        lambda_logger.error(f"Error handling request: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return build_api_response(event, 500, f"Error: {str(e)}")
