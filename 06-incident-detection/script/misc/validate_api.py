import boto3
import json
#import jwt
import requests
import time
#from jwt.algorithms import RSAAlgorithm

APP_CLIENT_ID = '66d65ehbusdl0mitclkvaccb5p'
REGION = 'us-west-2'
APIGW = 'https://am1fd2r1r0.execute-api.us-west-2.amazonaws.com'

cognito_idp = boto3.client('cognito-idp', region_name=REGION)

def authenticate_user(username, password):
    try:
        response = cognito_idp.initiate_auth(
            ClientId=APP_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        #print (response)
        if response.get('ChallengeName', 'xyz') == 'NEW_PASSWORD_REQUIRED':
           response = cognito_idp.respond_to_auth_challenge(
                               ClientId=APP_CLIENT_ID,
                               ChallengeName='NEW_PASSWORD_REQUIRED',
                               Session=response.get('Session'),
                               ChallengeResponses={'USERNAME':username, 'NEW_PASSWORD': 'We1come@1234', 'USER_ID_FOR_SRP': response.get('ChallengeParameters').get('USER_ID_FOR_SRP')}
                               )
           #print (response)
        return response['AuthenticationResult']['IdToken']
    except ClientError as e:
        print(f"Error authenticating user: {e}")
        return None

def lambda_handler(event, context):
    # This would be your API Gateway + Lambda function

    # Extract the JWT token from the Authorization header
    try:
        token = event['headers']['Authorization'].split(' ')[1]
    except (KeyError, IndexError):
        return {
            'statusCode': 401,
            'body': json.dumps('No valid Authorization header found')
        }

    get_sample(token)
    #post_sample(token)

def get_sample(token):
    headers = {'Authorization': f'{token}', 'Content-Type': 'application/json'}
    #print(headers)
    url = f'{APIGW}/prod/active-alerts'
    print (url)
    try:
       response = requests.get(url, headers = headers)
       response.raise_for_status()
       print(response.json())
    except requests.exceptions.RequestException as e:
       print (f"Error in calling /alerts API: {e}")
       return None

def post_sample(token):
    headers = {'Authorization': f'{token}', 'Content-Type': 'application/json'}
    #print(headers)
    url = f'{APIGW}/prod/post-sample'
    print (url)
    try:
       data = {'sample1':'sample1','sample2':'sample2'}
       response = requests.post(url, headers = headers,json=data)
       response.raise_for_status()
       print(response.json())
    except requests.exceptions.RequestException as e:
       print (f"Error in calling /alerts API: {e}")
       return None

# Example usage
if __name__ == "__main__":
    # This part would typically be done in your client application
    #username = "aj_rajkumar@yahoo.com"
    username = "test1@test.com"
    #username = "jrajk@amazon.com"
    #password = "We1come@1234"
    password = "Goodluck@76"
    
    token = authenticate_user(username, password)
    if token:
        print(f"Authentication successful.")
        
        # Simulate an API Gateway event
        event = {
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Call the Lambda handler
        result = lambda_handler(event, None)
        #print(result)

    else:
        print("Authentication failed")
