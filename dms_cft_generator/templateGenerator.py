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
from dms_cft_generator.utility.credentials_util import CredentialsUtil
from dms_cft_generator.utility.generic_util import *
from dms_cft_generator.utility.dms_util import *

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
    return True


def updateReplicationTaskDetailsInTemplate(inputJson, templateJson, tags_dict, credentials):
    templateJson['Resources']['ReplicationTask']['Properties']['MigrationType'] = inputJson['ReplicationTaskDetails'][
        'MigrationType']
    templateJson['Parameters']['ReplicationInstanceARN']['Default'] = get_appropriate_replication_instance(tags_dict,
                                                                                                           credentials)
    templateJson['Resources']['ReplicationTask']['Properties']['ReplicationTaskIdentifier'] = \
        inputJson['ReplicationTaskDetails']['ReplicationTaskIdentifier']


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
            dmsClient.start_replication_task(ReplicationTaskArn=replicationTaskArn,
                                             StartReplicationTaskType='start-replication')
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


def updateTargetEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials, tags_dict):
    #
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
    templateJson['Resources']['TargetEndpoint']['Properties']['Username'], \
    templateJson['Resources']['TargetEndpoint']['Properties'][
        'Password'] = credentials.get_credentials_from_secrets_manager(inputJson['TargetEndpointDetails']['SecretName'],
                                                                       tags_dict)
    templateJson['Resources']['TargetEndpoint']['Properties']['DatabaseName'] = inputJson['TargetEndpointDetails'][
        'DatabaseName']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create Replication Task.')
    parser.add_argument('--roleToAssume', action="store", dest="assumeRole", help='arn of the role to assume',
                        metavar='')
    ASSUME_ROLE = parser.parse_args().assumeRole
    credentials = CredentialsUtil(assume_role=ASSUME_ROLE, region="us-east-1")

    EXISTING_ENDPOINTS_TEMPLATE_FILE = json.loads(
        open(os.path.join(BASE_DIR, "templates", "dms-task-existing-endpoints-template.json")).read())
    NEW_ENDPOINTS_TEMPLATE_FILE = json.loads(
        open(os.path.join(BASE_DIR, "templates", "dms-task-new-endpoints-template.json")).read())

    accounts = os.listdir(os.path.join(BASE_DIR, "accounts"))
    for eachAccount in accounts:
        inputFileList = os.listdir(os.path.join(BASE_DIR, "accounts", eachAccount, "inputs"))
        # Deleting all files in outputs folder and recreating
        if os.path.exists(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs")):
            shutil.rmtree(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs"))
        os.makedirs(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs"))
        for eachInputFile in inputFileList:
            # TODO: change this one big try except
            try:
                with open(os.path.join(BASE_DIR, "accounts", eachAccount, "inputs", eachInputFile)) as eachInputJson:
                    inputJson = json.load(eachInputJson)
                    tags_dict = generate_dms_tags_dict(app_short_name="fsk", asset_id="2217")
                    templateType = validateInputJson(inputJson)
                    if inputJson['templateType'] and inputJson['templateType'] == "EXISTING_ENDPOINTS":
                        templateJson = copy.deepcopy(EXISTING_ENDPOINTS_TEMPLATE_FILE)
                        updateReplicationTaskDetailsInTemplate(inputJson, templateJson, tags_dict, credentials)
                        updateTableMappingInTemplate(inputJson, templateJson)
                        updateEndpointDetailsInExistingEndpointsTemplate(inputJson, templateJson)

                        outputTemplateFileName = str(eachInputFile.split('.')[0]) + "-cft.json"
                        with open(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs", outputTemplateFileName),
                                  'w') as outputFile:
                            json.dump(templateJson, outputFile)
                        deployCloudformation(templateJson, credentials.get_session())
                    elif inputJson['templateType'] == "NEW_ENDPOINTS":
                        templateJson = copy.deepcopy(NEW_ENDPOINTS_TEMPLATE_FILE)
                        updateReplicationTaskDetailsInTemplate(inputJson, templateJson, tags_dict, credentials)
                        updateTableMappingInTemplate(inputJson, templateJson)
                        updateSourceEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials,
                                                                          tags_dict)
                        updateTargetEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials,
                                                                          tags_dict)

                        outputTemplateFileName = str(eachInputFile.split('.')[0]) + "-cft.json"
                        with open(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs", outputTemplateFileName),
                                  'w') as outputFile:
                            json.dump(templateJson, outputFile, indent=4)

                        deployCloudformation(templateJson, credentials.get_session())
                    else:
                        print("Invalid templateType. Please check inputJson: "
                              + os.path.join(BASE_DIR, "accounts", eachAccount, "inputs", eachInputFile))
            except Exception as e:
                print("Unable to deploy CFT for inputFile: " + eachInputFile + " with error: " + str(e))
