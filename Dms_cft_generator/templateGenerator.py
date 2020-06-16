import copy
import json
import os
import shutil
import sys
import time
from collections import OrderedDict
from jsonschema import validate
import boto3
import argparse
import base64
from botocore.exceptions import ClientError

BASE_DIR = os.path.abspath(os.getcwd())


def validateInputJson(inputJson):
    # existingEndpointsTemplateSchema = json.loads(
    #     open(os.path.join(BASE_DIR, "schemas", "existing-endpoints-template-schema.json")).read())
    # try:
    #     validate(inputJson, existingEndpointsTemplateSchema)
    # except ...:
    #     print('invalid json')
    # else:
    #     print('valid json')
    # validate(instance={"type": "1","properties":{"price":{"type":1}}}, schema=existingEndpointsTemplateSchema)
    return inputJson['templateType']


def updateReplicationTaskDetailsInTemplate(inputJson, templateJson):
    print(inputJson['ReplicationTaskDetails'])
    templateJson['Resources']['ReplicationTask']['Properties']['MigrationType'] = inputJson['ReplicationTaskDetails'][
        'MigrationType']
    templateJson['Parameters']['ReplicationInstanceARN']['Default'] = inputJson['ReplicationTaskDetails'][
        'ReplicationInstanceArn']
    templateJson['Resources']['ReplicationTask']['Properties']['ReplicationTaskIdentifier'] = \
        inputJson['ReplicationTaskDetails']['ReplicationTaskIdentifier']


def updateTableMappingInTemplate(inputJson, templateJson):
    templateJson['Resources']['ReplicationTask']['Properties']['TableMappings'] = json.dumps(
        inputJson['TableMappings'])


def updateEndpointDetailsInExistingEndpointsTemplate(inputJson, templateJson):
    templateJson['Parameters']['SourceEndpointARN']['Default'] = inputJson['SourceEndpointDetails'][
        'SourceEndpointArn']
    templateJson['Parameters']['TargetEndpointARN']['Default'] = inputJson['TargetEndpointDetails'][
        'TargetEndpointArn']


def deployCloudformation(templateJson, ASSUME_ROLE):
    cloudFormationClient = boto3.client('cloudformation')
    dmsClient = boto3.client('dms')
    if ASSUME_ROLE:
        print("Assuming role " + ASSUME_ROLE + " for credentials")
        stsConnection = boto3.client('sts')
        stsCredentials = stsConnection.assume_role(RoleArn=ASSUME_ROLE, RoleSessionName="cp-deploy-role")
        ACCESS_KEY = stsCredentials['Credentials']['AccessKeyId']
        SECRET_KEY = stsCredentials['Credentials']['SecretAccessKey']
        SESSION_TOKEN = stsCredentials['Credentials']['SessionToken']

        cloudFormationClient = boto3.client('cloudformation', aws_access_key_id=ACCESS_KEY,
                                            aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN)
        dmsClient = boto3.client('dms', aws_access_key_id=ACCESS_KEY,
                                 aws_secret_access_key=SECRET_KEY, aws_session_token=SESSION_TOKEN)

    replicationTaskIdentifier = templateJson['Resources']['ReplicationTask']['Properties'][
        'ReplicationTaskIdentifier']
    stackName = replicationTaskIdentifier + "-DMS-stack"
    # Create cloud formation stack
    response = cloudFormationClient.create_stack(
        StackName=stackName,
        TemplateBody=json.dumps(templateJson),
        TimeoutInMinutes=10,
        Capabilities=['CAPABILITY_IAM']
    )

    print(response)
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
            dmsClient.start_replication_task(ReplicationTaskArn=replicationTaskArn,
                                             StartReplicationTaskType='start-replication')
            break
        elif stackStatus == 'CREATE_IN_PROGRESS' or stackStatus == 'UPDATE_IN_PROGRESS':
            print("Stack creation in progress. Sleeping 5secs!!!")
            time.sleep(5)
        else:
            print("Error creating cloudformation stack for replicationTask: " + replicationTaskIdentifier)
            break


def getPasswordFromPam(userName):
    # TODO: Do PAM integration here...
    return "dummypassword"


def updateSourceEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson):
    templateJson['Resources']['SourceEndpoint']['Properties']['ServerName'] = inputJson['SourceEndpointDetails'][
        'SourceUrl']
    templateJson['Resources']['SourceEndpoint']['Properties']['EndpointIdentifier'] = \
        inputJson['SourceEndpointDetails']['EndpointIdentifier']
    templateJson['Resources']['SourceEndpoint']['Properties']['EndpointType'] = "source"
    templateJson['Resources']['SourceEndpoint']['Properties']['EngineName'] = inputJson['SourceEndpointDetails'][
        'EngineName']
    templateJson['Resources']['SourceEndpoint']['Properties']['Port'] = inputJson['SourceEndpointDetails']['Port']
    templateJson['Resources']['SourceEndpoint']['Properties']['Username'] = inputJson['SourceEndpointDetails'][
        'Username']
    templateJson['Resources']['SourceEndpoint']['Properties']['Password'] = getPasswordFromPam(
        inputJson['SourceEndpointDetails']['Username'])
    templateJson['Resources']['SourceEndpoint']['Properties']['DatabaseName'] = inputJson['SourceEndpointDetails'][
        'DatabaseName']

    # templateJson['Resources']['SourceEndpoint']['Properties']['Port']


def getPasswordFromSecretsManager(param):
    secret_name = "OracleSecret"

    # Create a Secrets Manager client
    client = boto3.client(service_name='secretsmanager', region_name=r"us-east-1")
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            secret = base64.b64decode(get_secret_value_response['SecretBinary'])
    secretJson = json.loads(secret)
    return secretJson['password']


def updateTargetEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson):
    templateJson['Resources']['TargetEndpoint']['Properties']['ServerName'] = inputJson['TargetEndpointDetails'][
        'targetUrl']
    templateJson['Resources']['TargetEndpoint']['Properties']['EndpointIdentifier'] = \
        inputJson['TargetEndpointDetails']['EndpointIdentifier']
    templateJson['Resources']['TargetEndpoint']['Properties']['EndpointType'] = "target"
    templateJson['Resources']['TargetEndpoint']['Properties']['EngineName'] = inputJson['TargetEndpointDetails'][
        'EngineName']
    templateJson['Resources']['TargetEndpoint']['Properties']['Port'] = inputJson['TargetEndpointDetails']['Port']
    templateJson['Resources']['TargetEndpoint']['Properties']['Username'] = inputJson['TargetEndpointDetails'][
        'Username']
    templateJson['Resources']['TargetEndpoint']['Properties']['Password'] = getPasswordFromSecretsManager(
        inputJson['TargetEndpointDetails']['Username'])
    templateJson['Resources']['TargetEndpoint']['Properties']['DatabaseName'] = inputJson['TargetEndpointDetails'][
        'DatabaseName']

    # templateJson['Resources']['TargetEndpoint']['Properties']['Port']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create Replication Task.')
    parser.add_argument('--roleToAssume', action="store", dest="assumeRole", help='arn of the role to assume',
                        metavar='')
    ASSUME_ROLE = parser.parse_args().assumeRole

    EXISTING_ENDPOINTS_TEMPLATE_FILE = json.loads(
        open(os.path.join(BASE_DIR, "templates", "dms-task-existing-endpoints-template.json")).read())
    NEW_ENDPOINTS_TEMPLATE_FILE = json.loads(
        open(os.path.join(BASE_DIR, "templates", "dms-task-new-endpoints-template.json")).read())

    accounts = os.listdir(os.path.join(BASE_DIR, "accounts"))
    for eachAccount in accounts:
        inputFileList = os.listdir(os.path.join(BASE_DIR, "accounts", eachAccount, "inputs"))
        # Deleting all files in outputs folder and recreating
        shutil.rmtree(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs"))
        os.makedirs(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs"))
        for eachInputFile in inputFileList:
            with open(os.path.join(BASE_DIR, "accounts", eachAccount, "inputs", eachInputFile)) as eachInputJson:
                inputJson = json.load(eachInputJson)
                templateType = validateInputJson(inputJson)
                if templateType == "EXISTING_ENDPOINTS":
                    templateJson = copy.deepcopy(EXISTING_ENDPOINTS_TEMPLATE_FILE)
                    updateReplicationTaskDetailsInTemplate(inputJson, templateJson)
                    updateTableMappingInTemplate(inputJson, templateJson)
                    updateEndpointDetailsInExistingEndpointsTemplate(inputJson, templateJson)

                    outputTemplateFileName = str(eachInputFile.split('.')[0]) + "-cft.json"
                    with open(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs", outputTemplateFileName),
                              'w') as outputFile:
                        json.dump(templateJson, outputFile)
                    deployCloudformation(templateJson, ASSUME_ROLE)
                elif templateType == "NEW_ENDPOINTS":
                    templateJson = copy.deepcopy(NEW_ENDPOINTS_TEMPLATE_FILE)
                    updateReplicationTaskDetailsInTemplate(inputJson, templateJson)
                    updateTableMappingInTemplate(inputJson, templateJson)
                    updateSourceEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson)
                    updateTargetEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson)

                    outputTemplateFileName = str(eachInputFile.split('.')[0]) + "-cft.json"
                    with open(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs", outputTemplateFileName),
                              'w') as outputFile:
                        json.dump(templateJson, outputFile)
                    deployCloudformation(templateJson, ASSUME_ROLE)
                else:
                    print("Invalid templateType. Please check inputJson: " + os.path.join(BASE_DIR, "accounts",
                                                                                          eachAccount, "inputs",
                                                                                          eachInputFile))
