import base64
import copy
import json
import os
import time
import argparse
import os.path
from os import path

import boto3
from botocore.exceptions import ClientError
from jsonschema import validate

BASE_DIR = os.path.abspath(os.getcwd())


class CredentialsUtil:
    def __init__(self, **kwargs):
        ASSUME_ROLE = kwargs.get('assume_role', None)
        CREDENTIALS_PROFILE = kwargs.get('credentials_profile', None)
        REGION = kwargs.get('region', None)

        if CREDENTIALS_PROFILE:
            self.session = boto3.session.Session(profile_name=CREDENTIALS_PROFILE)
        elif ASSUME_ROLE:
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

    def get_credentials_from_secrets_manager(self, secret_name, tags_dict):
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


def get_appropriate_replication_instance(tags_dict, credentials: CredentialsUtil):
    # TODO: Handle Marker logic
    # TODO: Handle no instance found
    try:
        parsedDict = {}
        defaultReplicationInstance = "arn:aws:dms:us-east-1:464420198474:rep:6V4B6NMHFAN3HEDPL6ZODO6VXA"
        for eachDictTag in tags_dict:
            parsedDict[eachDictTag['Key']] = eachDictTag['Value']
        dmsClient = credentials.get_session().client('dms')
        replicationInstanceResponse = dmsClient.describe_replication_instances()
        for replicationInstance in replicationInstanceResponse['ReplicationInstances']:
            tagsResponse = dmsClient.list_tags_for_resource(ResourceArn=replicationInstance['ReplicationInstanceArn'])
            for eachTag in tagsResponse['TagList']:
                if eachTag['Key'] == "AppShortName" and eachTag['Value'] == parsedDict['AppShortName']:
                    defaultReplicationInstance = replicationInstance['ReplicationInstanceArn']
        return defaultReplicationInstance
    except Exception as e:
        print("Failed to get appropriate replication instance with error: " + str(e))
        # Remove this code later on
        print("Using default ReplicationInstance: arn:aws:dms:us-east-1:464420198474:rep:6V4B6NMHFAN3HEDPL6ZODO6VXA")
        return "arn:aws:dms:us-east-1:464420198474:rep:6V4B6NMHFAN3HEDPL6ZODO6VXA"


def updateReplicationTaskDetailsInTemplate(inputJson, templateJson, tags_dict, credentials):
    templateJson['Resources']['ReplicationTask']['Properties']['MigrationType'] = inputJson['ReplicationTaskDetails'][
        'MigrationType']
    templateJson['Parameters']['ReplicationInstanceARN']['Default'] = get_appropriate_replication_instance(tags_dict,
                                                                                                           credentials)
    templateJson['Resources']['ReplicationTask']['Properties']['ReplicationTaskIdentifier'] = \
        inputJson['ReplicationTaskDetails']['ReplicationTaskIdentifier']
    templateJson['Resources']['ReplicationTask']['Properties']['Tags'] = tags_dict


def updateTableMappingInTemplate(inputJson, templateJson):
    templateJson['Resources']['ReplicationTask']['Properties']['TableMappings'] = json.dumps(inputJson['TableMappings'])


def updateEndpointDetailsInExistingEndpointsTemplate(inputJson, templateJson):
    templateJson['Parameters']['SourceEndpointARN']['Default'] = inputJson['SourceEndpointDetails']['SourceEndpointArn']
    templateJson['Parameters']['TargetEndpointARN']['Default'] = inputJson['TargetEndpointDetails']['TargetEndpointArn']


def deployCloudformation(templateJson, session):
    cloudFormationClient = session.client('cloudformation')
    dmsClient = session.client('dms')

    replicationTaskIdentifier = templateJson['Resources']['ReplicationTask']['Properties']['ReplicationTaskIdentifier']
    stackName = replicationTaskIdentifier + "-DMS-stack"
    # Create cloud formation stack
    response = cloudFormationClient.create_stack(StackName=stackName, TemplateBody=json.dumps(templateJson),
                                                 TimeoutInMinutes=10, Capabilities=['CAPABILITY_IAM'])
    # Use this if we want to run same stack multiple times
    # response = client.update_stack(
    #     StackName='testStack',
    #     TemplateBody=json.dumps(templateJson),
    #     Capabilities=['CAPABILITY_IAM']
    # )

    while True:
        stackStatus = cloudFormationClient.describe_stacks(StackName=stackName)['Stacks'][0]['StackStatus']
        if stackStatus == 'CREATE_COMPLETE' or stackStatus == 'UPDATE_COMPLETE':
            replicationTaskArn = dmsClient.describe_replication_tasks(
                Filters=[{'Name': 'replication-task-id', 'Values': [replicationTaskIdentifier]}])[
                'ReplicationTasks'][0]['ReplicationTaskArn']
            try:
                dmsClient.start_replication_task(ReplicationTaskArn=replicationTaskArn,
                                                 StartReplicationTaskType='start-replication')
            except Exception as e:
                print("ERROR while starting replication task. Error: " + str(e))
            break
        elif stackStatus == 'CREATE_IN_PROGRESS' or stackStatus == 'UPDATE_IN_PROGRESS':
            print("Stack creation in progress. Sleeping 5secs!!!")
            time.sleep(5)
        else:
            print("Error creating cloudformation stack for replicationTask: " + replicationTaskIdentifier
                  + ". Stack status is " + stackStatus)
            break


def updateSourceEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials, tags_dict):
    templateJson['Resources']['SourceEndpoint']['Properties']['ServerName'] = inputJson['SourceEndpointDetails'][
        'SourceUrl']
    templateJson['Resources']['SourceEndpoint']['Properties']['EndpointIdentifier'] = \
        inputJson['SourceEndpointDetails']['EndpointIdentifier']
    templateJson['Resources']['SourceEndpoint']['Properties']['EndpointType'] = "source"
    templateJson['Resources']['SourceEndpoint']['Properties']['EngineName'] = inputJson['SourceEndpointDetails'][
        'EngineName']
    templateJson['Resources']['SourceEndpoint']['Properties']['Port'] = inputJson['SourceEndpointDetails']['Port']
    templateJson['Resources']['SourceEndpoint']['Properties']['Username'], \
    templateJson['Resources']['SourceEndpoint']['Properties']['Password'] = credentials.get_credentials_from_pam()
    templateJson['Resources']['SourceEndpoint']['Properties']['DatabaseName'] = inputJson['SourceEndpointDetails'][
        'DatabaseName']
    templateJson['Resources']['SourceEndpoint']['Properties']['Tags'] = tags_dict


def updateTargetEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials, tags_dict):
    #
    templateJson['Resources']['TargetEndpoint']['Properties']['ServerName'] = inputJson['TargetEndpointDetails'][
        'TargetUrl']
    templateJson['Resources']['TargetEndpoint']['Properties']['EndpointIdentifier'] = \
        inputJson['TargetEndpointDetails']['EndpointIdentifier']
    templateJson['Resources']['TargetEndpoint']['Properties']['EndpointType'] = "target"
    templateJson['Resources']['TargetEndpoint']['Properties']['EngineName'] = inputJson['TargetEndpointDetails'][
        'EngineName']
    templateJson['Resources']['TargetEndpoint']['Properties']['Port'] = inputJson['TargetEndpointDetails']['Port']
    templateJson['Resources']['TargetEndpoint']['Properties'][
        'Username'] = "{{resolve:secretsmanager:OracleSecret:SecretString:password}}"
    templateJson['Resources']['TargetEndpoint']['Properties'][
        'Password'] = "{{resolve:secretsmanager:OracleSecret:SecretString:username}}"
    templateJson['Resources']['TargetEndpoint']['Properties']['DatabaseName'] = inputJson['TargetEndpointDetails'][
        'DatabaseName']
    templateJson['Resources']['TargetEndpoint']['Properties']['Tags'] = tags_dict


def generate_dms_tags_dict(app_short_name, asset_id):
    return [{"Key": "AppShortName", "Value": app_short_name}, {"Key": "AssetId", "Value": asset_id}]


def validate_input_json(inputJson):
    BASE_DIR = os.path.abspath(os.getcwd())
    if inputJson['TemplateType'] == "NEW_ENDPOINTS":
        schemaFile = json.loads(open(os.path.join(BASE_DIR, "schemas", "new-endpoints-template-schema.json")).read())
    else:
        schemaFile = json.loads(open(os.path.join(BASE_DIR, "schemas", "new-endpoints-template-schema.json")).read())

    try:
        validate(instance=inputJson, schema=schemaFile)
    except Exception as e:
        print("Input validation failed with error: " + str(e))
        raise e


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create Replication Task.')
    parser.add_argument('--roleToAssume', action="store", dest="assumeRole", help='ARN of the role to assume',
                        metavar='')
    parser.add_argument('--credentialsProfile', action="store", dest="credentialsProfile",
                        help='AWS Credentials Profile to use', metavar='')
    parser.add_argument('--inputJsonPath', action="store", dest="inputJsonPath", help='Path of the input JSON file',
                        metavar='')
    parser.add_argument('--outputPath', action="store", dest="outputPath", help='Output Path for generated CFT',
                        metavar='')

    ASSUME_ROLE = parser.parse_args().assumeRole
    CREDENTIALS_PROFILE = parser.parse_args().credentialsProfile
    INPUT_JSON_PATH = parser.parse_args().inputJsonPath
    OUTPUT_CFT_PATH = parser.parse_args().outputPath

    credentials = CredentialsUtil(assume_role=ASSUME_ROLE, credentials_profile=CREDENTIALS_PROFILE, region='us-east-1')

    if path.exists(INPUT_JSON_PATH):
        try:
            with open(INPUT_JSON_PATH) as inputFile:
                inputJson = json.load(inputFile)
                tags_dict = generate_dms_tags_dict(app_short_name=inputJson['AppShortName'],
                                                   asset_id=inputJson['AssetId'])
                validate_input_json(inputJson)
                if inputJson['TemplateType'] == "EXISTING_ENDPOINTS":
                    EXISTING_ENDPOINTS_TEMPLATE_FILE = json.loads(
                        open(os.path.join(BASE_DIR, "templates", "dms-task-existing-endpoints-template.json")).read())
                    templateJson = copy.deepcopy(EXISTING_ENDPOINTS_TEMPLATE_FILE)
                    updateReplicationTaskDetailsInTemplate(inputJson, templateJson, tags_dict, credentials)
                    updateTableMappingInTemplate(inputJson, templateJson)
                    updateEndpointDetailsInExistingEndpointsTemplate(inputJson, templateJson)

                    outputTemplateFileName = "sampleOutput" + "-cft.json"
                    with open(os.path.join(OUTPUT_CFT_PATH, outputTemplateFileName), 'w') as outputFile:
                        json.dump(templateJson, outputFile, indent=4)
                    deployCloudformation(templateJson, credentials.get_session())
                elif inputJson['TemplateType'] == "NEW_ENDPOINTS":
                    NEW_ENDPOINTS_TEMPLATE_FILE = json.loads(
                        open(os.path.join(BASE_DIR, "templates", "dms-task-new-endpoints-template.json")).read())
                    templateJson = copy.deepcopy(NEW_ENDPOINTS_TEMPLATE_FILE)
                    updateReplicationTaskDetailsInTemplate(inputJson, templateJson, tags_dict, credentials)
                    updateTableMappingInTemplate(inputJson, templateJson)
                    updateSourceEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials, tags_dict)
                    updateTargetEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials, tags_dict)

                    outputTemplateFileName = "sampleOutput-new-endpoints" + "-cft.json"
                    with open(os.path.join(OUTPUT_CFT_PATH, outputTemplateFileName), 'w') as outputFile:
                        json.dump(templateJson, outputFile, indent=4)
                    deployCloudformation(templateJson, credentials.get_session())
                else:
                    print("Invalid templateType. Please check inputJson: " + inputJson)
        except Exception as e:
            print("Unable to parse inputFile: " + INPUT_JSON_PATH + ", error: " + str(e))
    else:
        print("Input path does not exists")
