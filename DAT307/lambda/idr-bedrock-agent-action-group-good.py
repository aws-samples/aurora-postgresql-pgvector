import json
import os
import boto3
import logging
import traceback
import psycopg2
from psycopg2.extras import RealDictCursor
from botocore.client import Config
import datetime
from datetime import datetime, timedelta

config = Config(connect_timeout=5, retries={'max_attempts': 0})

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
lambda_logger = logging.getLogger(__name__)

if lambda_logger.hasHandlers():
    lambda_logger.setLevel(LOG_LEVEL)
else:
    logging.basicConfig(level=LOG_LEVEL)

region_name = os.environ['AWS_REGION']

rdsClient = boto3.client('rds',region_name=region_name,config=config)
secretsClient = boto3.client('secretsmanager', region_name=region_name,config=config)
cloudwatchClient = boto3.client('cloudwatch', region_name=region_name,config=config)


classOrder = ['micro','small','medium','large','xlarge','2xlarge','4xlarge','8xlarge','12xlarge','16xlarge','14xlarge','32xlarge','na']

#==============================================================================================================================            
# Helper functions

def get_connection_str(db_instance_identifier):
    response = secretsClient.get_secret_value(SecretId=f'{db_instance_identifier}-agent-secret')
    database_secrets = json.loads(response['SecretString'])
    dbhost = database_secrets['host']
    dbport = database_secrets['port']
    dbuser = database_secrets['username']
    dbpass = database_secrets['password']
    cs = "user=%s password=%s host=%s port=%s" % (dbuser,dbpass,dbhost,dbport)
    return cs

def get_param(parameters, parameter):
    param_value = None
    for param in parameters:
        if param["name"] == parameter:
            param_value = param["value"]
    if not param_value:
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

def getNextInstanceClass(db_instance_identifier, currentClass):
    
    #currentClass = "db.t3.2xlarge"
    getClass = currentClass.split(".")[2]
    
    nextClass = None
    
    for index, instanceClass in enumerate(classOrder):
        if instanceClass == getClass:
            nextClass = classOrder[index+1]
            break
    
    lambda_logger.info(f"Checking the availability of {nextClass}")
    if nextClass is None:
        return "NA"
    if nextClass == "na":
        return "NA"
    
    nextClass = f"{currentClass.split(".")[0]}.{currentClass.split(".")[1]}.{nextClass}"
    lambda_logger.info(f"Checking the availability of {nextClass}")
    
    response = get_instance_details_helper(db_instance_identifier)
    engine = response['Engine']
    engineVersion = response['EngineVersion']
    
    response = rdsClient.describe_orderable_db_instance_options(
        Engine = engine,
        EngineVersion = engineVersion,
        Vpc = True,
        DBInstanceClass = nextClass)
        
    if len(response['OrderableDBInstanceOptions']) > 1 :
        lambda_logger.info(f"Next available instance class is {nextClass}")
        return nextClass
        
    lambda_logger.error("Next available instance is not present in the repository")
    raise Exception("Next available instance is not present in the repository")
    
    
def get_instance_details_helper(db_instance_identifier):
    try:
        response = rdsClient.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
        return response['DBInstances'][0]
    except Exception as e:
        lambda_logger.error(f"Unable to get the instance details: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"
        
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


def get_max_acu_helper(db_instance_identifier):
    try:
        dbClusterName = get_cluster_name(db_instance_identifier)
        clusterResponse = get_cluster_details_helper(dbClusterName)
        maxACU = clusterResponse['ServerlessV2ScalingConfiguration']['MaxCapacity']
        return maxACU
    except Exception as e:
        lambda_logger.error(f"Unable to get the cluster maxACU details: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"    

#==============================================================================================================================            
    
# Action group functions

def check_rds_state(db_instance_identifier):
    """
      Function to check the current state of the RDS cluster 
    """
    try:
        
        response = get_instance_details_helper(db_instance_identifier)
        status = response['DBInstanceStatus']
        message = f"The RDS status is {status}."
        if status != 'available':
            message += " It is unavailable state, please try again later."
        lambda_logger.info(message)
        return message
    except Exception as e:
        lambda_logger.error(f"Error checking status: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return f"Error: {str(e)}"


def get_allocated_storage_size(db_instance_identifier):
    """
      Function to get the current storage size of RDS Cluster
    """
    try:
        response = get_instance_details_helper(db_instance_identifier)
        storage_size = response['AllocatedStorage']
        message = f"Allocated storage size is {storage_size} GB."
        lambda_logger.info(message)
        return message
    except Exception as e:
        lambda_logger.error(f"Error retrieving storage size: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return f"Error: {str(e)}"


def get_provisioned_iops(db_instance_identifier):
    """
      Function to get the provisioned IOPS
    """
    try:
        response = get_instance_details_helper(db_instance_identifier)
        iops = response['Iops']
        message = f"Provisioned IOPS is {iops} ."
        lambda_logger.info(message)
        return message
    except Exception as e:
        lambda_logger.error(f"Error retrieving iops: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return f"Error: {str(e)}"


def get_current_storage_size(db_instance_identifier):
    """
      Function to get the current storage size of RDS Cluster.
    """
    
    response = get_instance_details_helper(db_instance_identifier)
    allocated_storage_size = response['AllocatedStorage']

    start_date =  datetime.utcnow() - timedelta(minutes=5)
    end_date = datetime.utcnow()
    response = cloudwatchClient.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'myrequest',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': 'FreeStorageSpace',
                        'Dimensions': [
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': db_instance_identifier
                            },
                        ]
                    },
                    'Period': 300,
                    'Stat': 'Maximum'
                }
            },
        ],
        StartTime=start_date, 
        EndTime=end_date,    
    )
    current_free_storage = int(response["MetricDataResults"][0]['Values'][0]/1024/1024/1024)
    current_storage = allocated_storage_size - current_free_storage
    lambda_logger.info(current_storage)
    return f"Current  storage is {current_storage} GB"

def increase_storage_size(db_instance_identifier, percent_increase):
    """
      Function to increase the volume size RDS Cluster with the passed new storage
    """
    try:
        response = get_instance_details_helper(db_instance_identifier)
        iops = response['Iops']
        allocatedStorage = response['AllocatedStorage']
        new_storage_size = allocatedStorage + allocatedStorage*int(percent_increase)/100
        
        response = rdsClient.modify_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            AllocatedStorage=int(new_storage_size),
            ApplyImmediately=True,
            Iops=iops
        )
        message = f"Initiated storage volume size increase to {new_storage_size} GB."
        lambda_logger.info(message)
        return message
    except Exception as e:
        lambda_logger.error(f"Error increasing volume size: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return f"Error: {str(e)}"


def get_instance_details(db_instance_identifier):
    """
      Function to retrieve the instance details of RDS Cluster. Output will be in json format 
    """
    try:
        response = get_instance_details_helper(db_instance_identifier)
        return json.dumps(response, indent=4, sort_keys=True, default=str)
    except Exception as e:
        lambda_logger.error(f"Unable to get the instance details: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"


def get_environment_tag(db_instance_identifier):
    """
      Function to retrieve the current environment of the RDS cluster
    """
    try:
        env = None
        message = f"Instance {db_instance_identifier} environment is not defined"
        response = get_instance_details_helper(db_instance_identifier)
        if len(response['TagList']) == 0:
            lambda_logger.info(message)
            return message
        for tag in response['TagList']:
            if tag['Key'] == 'Environment':
                env = tag['Value']
        
        if env is None:
            lambda_logger.info(message)
            return message
        
        message = f"Instance {db_instance_identifier} environment is {env}"
        lambda_logger.info(message)
        return message
        
    except Exception as e:
        lambda_logger.error(f"Unable to get the environment details: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"


def run_query(db_instance_identifier,query):
    """
      Function to get the authentication from the secrets manager and run the query passed and provide the result set.
      It expectes the secrets to be available in the format <db_instance_identifier>-agent-secret
    """
 
    try:
        conn_str = get_connection_str(db_instance_identifier)
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query)
        results = cur.fetchall()
        return results
        
    except Exception as e:
        lambda_logger.error(f"Unable to run the query in the instance : {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"
    
def get_cpu_metrics(db_instance_identifier, metric_time):
    
    start_date =  datetime.utcnow() - timedelta(hours=int(metric_time))
    end_date = datetime.utcnow()
    period = int(metric_time)*60*60 
    response = cloudwatchClient.get_metric_data(
        MetricDataQueries=[
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
                    'Stat': 'Maximum'
                }
            },
        ],
        StartTime=start_date, 
        EndTime=end_date,    
    )
    #metric_timestamps = response["MetricDataResults"][0]['Timestamps']
    #metric_values = response["MetricDataResults"][0]['Values']
    #merged_list = [(metric_timestamps[i].isoformat(), metric_values[i]) for i in range(0, len(metric_timestamps))]
    #return merged_list
    metric_value = int(response["MetricDataResults"][0]['Values'][0])
    return f"Maximum CPU utilization is {metric_value}%"
    
def get_iops_metrics(db_instance_identifier, metric_time):
    start_date =  datetime.utcnow() - timedelta(hours=int(metric_time))
    end_date = datetime.utcnow()
    period = int(metric_time)*60*60 
    response = cloudwatchClient.get_metric_data(
        MetricDataQueries=[
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
                    "Stat": "Maximum"
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
                    "Stat": "Maximum",
                },
                "ReturnData": False
            }
        ],
        StartTime=start_date, 
        EndTime=end_date,    
    )
    #metric_timestamps = response["MetricDataResults"][0]['Timestamps']
    #metric_values = response["MetricDataResults"][0]['Values']
    #merged_list = [(metric_timestamps[i].isoformat(), metric_values[i]) for i in range(0, len(metric_timestamps))]
    metric_value = int(response["MetricDataResults"][0]['Values'][0])
    return f"Maximum IOPS utilization is {metric_value}"

def scale_up_instance(db_instance_identifier):
    try:
        # Get the current instance type
        response = get_instance_details_helper(db_instance_identifier)
        currentInstanceClass =  response['DBInstanceClass']
        nextInstanceClass = getNextInstanceClass(db_instance_identifier, currentInstanceClass)
        if nextInstanceClass == "NA":
            lambda_logger.error("Unable to get the next instance Class")
            return "Unable to get the next instance Class or it is not available"
        
        lambda_logger.info(f"Scaling up the instance {db_instance_identifier} to {nextInstanceClass}")
        modResponse = rdsClient.modify_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            DBInstanceClass=nextInstanceClass,
            ApplyImmediately = True)
        lambda_logger.info(modResponse)
        return "Submitted the request to scale up the instance to {nextInstanceClass} class"
    except Exception as e:
        lambda_logger.error(f"Unable to get the next instance class : {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"


def increase_iops(db_instance_identifier, percent_increase):
    try:
        # Get the current instance type
        response = get_instance_details_helper(db_instance_identifier)
        currentIops =  response['Iops']
        lambda_logger.info(currentIops)
        lambda_logger.info(percent_increase)
        
        allocatedStorage = response['AllocatedStorage']
        newIops = currentIops + int(currentIops*int(percent_increase)/100)
        lambda_logger.info(f"Going to increase the IOPS to {newIops} for the RDS instance {db_instance_identifier}")
        modResponse = rdsClient.modify_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            Iops=newIops,
            AllocatedStorage = allocatedStorage,
            ApplyImmediately = True)
        lambda_logger.info(modResponse)
        return f"Submitted the request to increase IOPS by {percent_increase}%"
    except Exception as e:
        lambda_logger.error(f"Unable to increase the IOPS : {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"

#-- Add function definition here ---
def get_max_acu(db_instance_identifier):
    try:
        maxACU = get_max_acu_helper(db_instance_identifier)
        message = f"Max ACU utilization of the instance {db_instance_identifier} is {maxACU}"
        lambda_logger.info(message)
        return message
    except Exception as e:
        lambda_logger.error(f"Unable to get the maxACU instance class : {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"  

def get_acu_metrics(db_instance_identifier, metric_time):
    start_date =  datetime.utcnow() - timedelta(hours=int(metric_time))
    end_date = datetime.utcnow()
    period = int(metric_time)*60*60 
    response = cloudwatchClient.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'myrequest',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/RDS',
                        'MetricName': 'ACUUtilization',
                        'Dimensions': [
                            {
                                'Name': 'DBInstanceIdentifier',
                                'Value': db_instance_identifier
                            },
                        ]
                    },
                    'Period': period,
                    'Stat': 'Maximum'
                }
            },
        ],
        StartTime=start_date, 
        EndTime=end_date,    
    )
    metric_value = int(response["MetricDataResults"][0]['Values'][0])
    return f"Maximum ACU utilization is {metric_value}"
    
def increase_acu(db_instance_identifier, percent_increase):
    try:
        maxACU = get_max_acu_helper(db_instance_identifier)
        newMaxACU = maxACU + int(maxACU*int(percent_increase)/100)
        if maxACU == newMaxACU:
            newMaxACU = newMaxACU + 1
        dbClusterName = get_cluster_name(db_instance_identifier)
        lambda_logger.info(f"Going to increase the maxACU to {newMaxACU} for the cluster {dbClusterName}")
        modResponse = rdsClient.modify_db_cluster(
            DBClusterIdentifier=dbClusterName,
            ServerlessV2ScalingConfiguration={
                'MaxCapacity': newMaxACU
             },
            ApplyImmediately = True)
        lambda_logger.info(modResponse)
        return f"Submitted the request to increase maxACU to {newMaxACU} by {percent_increase}%"
    except Exception as e:
        lambda_logger.error(f"Unable to increase the maxACU : {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return  f"Error: {str(e)}"
#-- End of function defintion ----
#==============================================================================================================================            

def lambda_handler(event, context):
    try:
        lambda_logger.info(f"Received event: {event}")
        #path = event.get("apiPath")
        #method = event.get("httpMethod")

        agent = event['agent']
        actionGroup = event['actionGroup']
        function = event['function']
        parameters = event.get('parameters', [])
        print(event)
        print(context)
        responseMessage = None
        
        db_instance_identifier = None
        new_storage_size = None
        
        if function == "get_instance_details":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            responseMessage = get_instance_details(db_instance_identifier)

        if function == "check_rds_state":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            responseMessage = check_rds_state(db_instance_identifier)

        if function == "get_allocated_storage_size":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            responseMessage = get_allocated_storage_size(db_instance_identifier)

        if function == "get_current_storage_size":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            responseMessage = get_current_storage_size(db_instance_identifier)

        if function == "increase_storage_size":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            percent_increase = get_param(parameters, "percent_increase")
            responseMessage = increase_storage_size(db_instance_identifier, percent_increase)

        if function == "run_query":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            query = get_param(parameters, "query")
            responseMessage = run_query(db_instance_identifier, query)

        if function == "get_cpu_metrics":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            metric_time = get_param(parameters, "metric_time")
            responseMessage = get_cpu_metrics(db_instance_identifier,metric_time)

        if function == "get_iops_metrics":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            metric_time = get_param(parameters, "metric_time")
            responseMessage = get_iops_metrics(db_instance_identifier,metric_time)

        if function == "scale_up_instance":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            responseMessage = scale_up_instance(db_instance_identifier)

        if function == "increase_iops":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            percent_increase = get_param(parameters, "percent_increase")
            responseMessage = increase_iops(db_instance_identifier,percent_increase)
            
        if function == "get_provisioned_iops":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            responseMessage = get_provisioned_iops(db_instance_identifier)

        if function == "get_environment_tag":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            responseMessage = get_environment_tag(db_instance_identifier)

#-- Add function call here ---
        if function == "increase_acu":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            percent_increase = get_param(parameters, "percent_increase")
            responseMessage = increase_acu(db_instance_identifier,percent_increase)

        if function == "get_max_acu":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            responseMessage = get_max_acu(db_instance_identifier)
            
        if function == "get_acu_metrics":
            db_instance_identifier = get_param(parameters, "db_instance_identifier")
            metric_time = get_param(parameters, "metric_time")
            responseMessage = get_acu_metrics(db_instance_identifier,metric_time)
#-- End of function call ---

        lambda_logger.info(f"Response: {responseMessage}")
        return build_api_response(event, 200, str(responseMessage))

    except Exception as e:
        lambda_logger.error(f"Error handling request: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return build_api_response(event, 500, f"Error: {str(e)}")

