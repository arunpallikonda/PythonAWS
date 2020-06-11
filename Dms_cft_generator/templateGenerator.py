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


def deployCloudformation(templateJson):
    cloudFormationClient = boto3.client('cloudformation', aws_access_key_id=ACCESS_KEY,
                                        aws_secret_access_key=SECRET_KEY,
                                        aws_session_token=SESSION_TOKEN)
    dmsClient = boto3.client('dms', aws_access_key_id=ACCESS_KEY,
                             aws_secret_access_key=SECRET_KEY,
                             aws_session_token=SESSION_TOKEN)
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


def getpassword(userName):
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
    templateJson['Resources']['SourceEndpoint']['Properties']['Password'] = getpassword(
        inputJson['SourceEndpointDetails']['Username'])

    # templateJson['Resources']['SourceEndpoint']['Properties']['Port']


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
    templateJson['Resources']['TargetEndpoint']['Properties']['Password'] = getpassword(
        inputJson['TargetEndpointDetails']['Username'])

    # templateJson['Resources']['TargetEndpoint']['Properties']['Port']


if __name__ == '__main__':

    # parser = argparse.ArgumentParser(description='Process some integers.')
    # parser.add_argument('integers', metavar='N', type=int, nargs='+',
    #                     help='an integer for the accumulator')
    # parser.add_argument('--sum', dest='accumulate', action='store_const',
    #                     const=sum, default=max,
    #                     help='sum the integers (default: find the max)')
    # args = parser.parse_args()
    # print(args.accumulate(args.integers))

    sts_connection = boto3.client('sts')
    stsCredentials = sts_connection.assume_role(RoleArn="arn:aws:iam::464420198474:role/dms_role_to_assume",
                                                RoleSessionName="cp-deploy-role")
    ACCESS_KEY = stsCredentials['Credentials']['AccessKeyId']
    SECRET_KEY = stsCredentials['Credentials']['SecretAccessKey']
    SESSION_TOKEN = stsCredentials['Credentials']['SessionToken']

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
                    deployCloudformation(templateJson)
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
                    deployCloudformation(templateJson)
                else:
                    print("Invalid templateType. Please check inputJson: " + os.path.join(BASE_DIR, "accounts",
                                                                                          eachAccount, "inputs",
                                                                                          eachInputFile))
