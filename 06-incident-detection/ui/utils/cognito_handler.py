import streamlit as st
from dotenv import load_dotenv
import os
import boto3
from botocore.exceptions import ClientError

load_dotenv()
APP_CLIENT_ID=os.getenv('APP_CLIENT_ID')
USER_POOL_ID = os.getenv('USER_POOL_ID')
AWS_REGION=os.getenv('AWS_REGION')

cognito_idp_client = boto3.client('cognito-idp', region_name=AWS_REGION)
        
def authenticate_user(username="demo@dat307.com", password="Welcome@reInvent2024"):
    try:
        response = cognito_idp_client.initiate_auth(
            ClientId=APP_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={ 'USERNAME': username,'PASSWORD': password }
        )
        print (response)
        return True, response['AuthenticationResult']['IdToken'], None
    except ClientError as err:
        print(f"Couldn't login {username} due to {err.response['Error']['Message']}")
        return False, None, err.response["Error"]["Message"]

def sign_up_user(username, password):
    try:
        kwargs = {
                "ClientId": APP_CLIENT_ID,
                "Username": username,
                "Password": password,
                "UserAttributes": [{"Name": "email", "Value": username}],
            }
        response = cognito_idp_client.sign_up(**kwargs)
        print(response)
        confirmed = response["UserConfirmed"]
        print(f"Created the user {username} successfully")
        return True, None
    
    except ClientError as err:
        if err.response["Error"]["Code"] == "UsernameExistsException":
             print(f"Couldn't sign up {username}. {err.response['Error']['Message']}")
             return False, err.response["Error"]["Message"]
         
        print(f"Couldn't sign up {username}. {err.response['Error']['Message']}")
        return False, err.response["Error"]["Message"]
