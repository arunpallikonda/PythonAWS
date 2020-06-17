import base64
import json

import boto3
from botocore.exceptions import ClientError


class CredentialsUtil:
    def __init__(self, **kwargs):
        ASSUME_ROLE = kwargs.get('assume_role', None)
        REGION = kwargs.get('region', None)

        if ASSUME_ROLE:
            print("Assuming role " + ASSUME_ROLE + " for credentials")
            stsConnection = boto3.client('sts')
            stsCredentials = stsConnection.assume_role(RoleArn=ASSUME_ROLE, RoleSessionName="dmsauto-assume-role")
            ACCESS_KEY = stsCredentials['Credentials']['AccessKeyId']
            SECRET_KEY = stsCredentials['Credentials']['SecretAccessKey']
            SESSION_TOKEN = stsCredentials['Credentials']['SessionToken']

            self.session = boto3.session.Session(aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY,
                                                 aws_session_token=SESSION_TOKEN, region_name=REGION)
        else:
            self.session = boto3.Session(region_name=REGION)

    def get_session(self):
        return self.session

    def get_credentials_from_secrets_manager(self, secret_name):
        secret, username, password = [None] * 3
        # Create a Secrets Manager client
        secrets_client = self.session.client(service_name='secretsmanager')
        try:
            get_secret_value_response = secrets_client.get_secret_value(SecretId=secret_name)
        except ClientError as e:
            raise e
        else:
            if 'SecretString' in get_secret_value_response:
                secret = get_secret_value_response['SecretString']
            else:
                secret = base64.b64decode(get_secret_value_response['SecretBinary'])
        if secret:
            secretJson = json.loads(secret)
            username = secretJson['username']
            password = secretJson['password']
        return username, password

    def get_credentials_from_pam(self):
        return "sampleUser", "samplePassword"
