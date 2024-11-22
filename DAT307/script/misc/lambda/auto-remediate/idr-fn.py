import json
import os
import boto3
import logging
import traceback

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
lambda_logger = logging.getLogger(__name__)

if lambda_logger.hasHandlers():
    lambda_logger.setLevel(LOG_LEVEL)
else:
    logging.basicConfig(level=LOG_LEVEL)

client = boto3.client('rds')
db_instance_identifier = os.getenv("DB_IDENTIFIER", "rdspg1")


def check_rds_status(db_instance_identifier):
    try:
        response = client.describe_db_instances(
            DBInstanceIdentifier=db_instance_identifier
        )
        status = response['DBInstances'][0]['DBInstanceStatus']
        message = f"The RDS status is {status}."
        if status != 'available':
            message += " It is not in available state, please try again later."
        lambda_logger.info(message)
        return {"status": status, "message": message}
    except Exception as e:
        lambda_logger.error(f"Error checking status: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return {"status": "error", "message": f"Error: {str(e)}"}


def get_current_storage_size(db_instance_identifier):
    try:
        response = client.describe_db_instances(
            DBInstanceIdentifier=db_instance_identifier
        )
        storage_size = response['DBInstances'][0]['AllocatedStorage']
        message = f"Current storage size is {storage_size} GB."
        lambda_logger.info(message)
        return {"body": message}
    except Exception as e:
        lambda_logger.error(f"Error retrieving storage size: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return {"body": f"Error: {str(e)}"}


def increase_volume_size(db_instance_identifier, new_storage_size):
    try:
        iops = client.describe_db_instances(
            DBInstanceIdentifier=db_instance_identifier
        )['DBInstances'][0]['Iops']

        response = client.modify_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            AllocatedStorage=int(new_storage_size),
            ApplyImmediately=True,
            Iops=iops
        )
        message = f"Initiated volume size increase to {new_storage_size} GB."
        lambda_logger.info(message)
        return {"body": message}
    except Exception as e:
        lambda_logger.error(f"Error increasing volume size: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return {"body": f"Error: {str(e)}"}


def rollback_to_original_size(db_instance_identifier, old_storage_size):
    try:
        response = client.modify_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            AllocatedStorage=old_storage_size,
            ApplyImmediately=True
        )
        message = f"Rolled back storage size to {old_storage_size} GB."
        lambda_logger.info(message)
        return {"body": message}
    except Exception as e:
        lambda_logger.error(f"Error rolling back volume size: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return {"body": f"Error: {str(e)}"}


def extract_value(parameters, param_name):
    """
    Helper function to extract the value of a parameter from the event's parameters.
    TODO: can be abstracted as a lib
    """
    for param in parameters:
        if param['name'] == param_name:
            return param['value']
    return None


def build_api_response(event, status_code, response_message):
    """
    Helper function to build the structured API response.
    TODO: can be abstracted as a lib
    """
    response_body = {
        'application/json': {
            'body': response_message
        }
    }

    action_response = {
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': status_code,
        'responseBody': response_body
    }

    api_response = {
        'messageVersion': '1.0',
        'response': action_response,
        'sessionAttributes': event['sessionAttributes'],
        'promptSessionAttributes': event['promptSessionAttributes']
    }

    return api_response


def lambda_handler(event, context):
    try:
        lambda_logger.info(f"Received event: {event}")
        path = event.get("apiPath")
        method = event.get("httpMethod")
        parameters = event.get("parameters", [])

        # POST calls
        properties = event.get("requestBody", {}).get("content", {}).get("application/json", {}).get("properties", [])

        db_instance_identifier = extract_value(properties, 'db_instance_identifier') or os.getenv("DB_IDENTIFIER",
                                                                                                  "rdspg1") or extract_value(
            parameters, 'db_instance_identifier')

        if not db_instance_identifier:
            error_message = "Missing db_instance_identifier parameter."
            lambda_logger.error(error_message)
            return build_api_response(event, 400, error_message)

        # Route the requests to the correct function based on the path and method
        if path == "/check-rds-status" and method == "GET":
            result = check_rds_status(db_instance_identifier)
            lambda_logger.info(f"Response: {result}")
            return build_api_response(event, 200, result['message'])

        elif path == "/get-current-storage-size" and method == "GET":
            result = get_current_storage_size(db_instance_identifier)
            lambda_logger.info(f"Response: {result}")
            return build_api_response(event, 200, result['body'])

        elif path == "/increase-volume-size" and method == "POST":
            new_storage_size = extract_value(properties, 'new_storage_size')
            if not new_storage_size:
                error_message = "Missing new_storage_size parameter."
                lambda_logger.error(error_message)
                return build_api_response(event, 400, error_message)

            status_result = check_rds_status(db_instance_identifier)
            if status_result['status'] != 'available':
                lambda_logger.info(f"RDS is not available: {status_result['message']}")
                return build_api_response(event, 200, status_result['message'])

            result = increase_volume_size(db_instance_identifier, new_storage_size)
            lambda_logger.info(f"Response: {result}")
            return build_api_response(event, 200, result['body'])

        elif path == "/rollback-to-original-size" and method == "POST":
            old_storage_size = extract_value(properties, 'old_storage_size')
            if not old_storage_size:
                error_message = "Missing old_storage_size parameter."
                lambda_logger.error(error_message)
                return build_api_response(event, 400, error_message)

            result = rollback_to_original_size(db_instance_identifier, old_storage_size)
            lambda_logger.info(f"Response: {result}")
            return build_api_response(event, 200, result['body'])

        else:
            error_message = "Invalid request"
            lambda_logger.error(error_message)
            return build_api_response(event, 400, error_message)

    except Exception as e:
        lambda_logger.error(f"Error handling request: {str(e)}")
        lambda_logger.error(traceback.format_exc())
        return build_api_response(event, 500, f"Error: {str(e)}")
