import copy
import json
import os
import sys
import time
from collections import OrderedDict
from jsonschema import validate
import boto3

BASE_DIR = os.path.abspath(os.getcwd())


def validateInputJson(inputJson):
    existingEndpointsTemplateSchema = json.loads(
        open(os.path.join(BASE_DIR, "schemas", "existing-endpoints-template-schema.json")).read())
    # try:
    #     validate(inputJson, existingEndpointsTemplateSchema)
    # except ...:
    #     print('invalid json')
    # else:
    #     print('valid json')
    # validate(instance={"type": "1","properties":{"price":{"type":1}}}, schema=existingEndpointsTemplateSchema)
    return "EXISTING_ENDPOINTS_INPUT"


def createExistingEndpointsReplicationTaskCft(migrationType, replicationInstanceArn, replicationTaskName, tableMapping,
                                              sourceEndpointArn, targetEndpointArn):
    templateJson = copy.deepcopy(EXISTING_ENDPOINTS_TEMPLATE_FILE)
    templateJson['Parameters']['ReplicationInstanceARN']['Default'] = replicationInstanceArn
    templateJson['Parameters']['SourceEndpointARN']['Default'] = sourceEndpointArn
    templateJson['Parameters']['TargetEndpointARN']['Default'] = targetEndpointArn

    templateJson['Resources']['ReplicationTask']['Properties']['ReplicationTaskIdentifier'] = replicationTaskName
    templateJson['Resources']['ReplicationTask']['Properties']['MigrationType'] = migrationType
    templateJson['Resources']['ReplicationTask']['Properties']['TableMappings'] = tableMapping
    return templateJson


def extractReplicationTaskDetailsForExistingEndpointTemplate(inputJson):
    print(inputJson['ReplicationTaskDetails'])
    return [inputJson['ReplicationTaskDetails']['MigrationType'],
            inputJson['ReplicationTaskDetails']['ReplicationInstanceArn'],
            inputJson['ReplicationTaskDetails']['ReplicationTaskIdentifier']]


def extractTableMappingForExistingEndpointTemplate(inputJson):
    return json.dumps(inputJson['TableMappings'])


def extractEndpointDetailsForExistingEndpointTemplates(inputJson):
    return [inputJson['SourceEndpointDetails']['SourceEndpointArn'],
            inputJson['TargetEndpointDetails']['TargetEndpointArn']]


def deployCloudformation(templateJson):
    cloudFormationClient = boto3.client('cloudformation')
    dmsClient = boto3.client('dms')
    replicationTaskIdentifier = templateJson['Resources']['ReplicationTask']['Properties']['ReplicationTaskIdentifier']
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
                Filters=[{'Name': 'ReplicationTaskIdentifier', 'Values': [replicationTaskIdentifier]}])[
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


if __name__ == '__main__':
    EXISTING_ENDPOINTS_TEMPLATE_FILE = json.loads(
        open(os.path.join(BASE_DIR, "templates", "dms-task-existing-endpoints-template.json")).read())

    accounts = os.listdir(os.path.join(BASE_DIR, "accounts"))
    for eachAccount in accounts:
        inputFileList = os.listdir(os.path.join(BASE_DIR, "accounts", eachAccount, "inputs"))
        for eachInputFile in inputFileList:
            with open(os.path.join(BASE_DIR, "accounts", eachAccount, "inputs", eachInputFile)) as eachInputJson:
                inputJson = json.load(eachInputJson)
                templateType = validateInputJson(inputJson)
                print("After validation")
                if templateType and templateType == "EXISTING_ENDPOINTS_INPUT":
                    migrationType, replicationInstanceArn, replicationTaskName = extractReplicationTaskDetailsForExistingEndpointTemplate(
                        inputJson)
                    tableMapping = extractTableMappingForExistingEndpointTemplate(inputJson)
                    sourceEndpointArn, targetEndpointArn = extractEndpointDetailsForExistingEndpointTemplates(inputJson)

                    templateJson = createExistingEndpointsReplicationTaskCft(migrationType, replicationInstanceArn,
                                                                             replicationTaskName, tableMapping,
                                                                             sourceEndpointArn, targetEndpointArn)
                    outputTemplateFileName = str(eachInputFile.split('.')[0]) + "-cft.json"
                    with open(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs", outputTemplateFileName),
                              'w') as outputFile:
                        json.dump(templateJson, outputFile)
                    deployCloudformation(templateJson)
