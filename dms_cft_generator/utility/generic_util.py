import json
import os
import string
import random
import logging
from os.path import isfile, join

import botocore
from jsonschema import validate


def read_json_file(path, file):
    current_path = os.path.abspath((os.path.dirname(file)))
    return json.loads(open(os.path.join(current_path, path)).read())


def delete_cloudformation_stack(cloudFormationClient, stackName):
    try:
        cloudFormationClient.delete_stack(StackName=stackName)
        print("Deleting the stack: %s" % stackName)
        waiter = cloudFormationClient.get_waiter('stack_delete_complete')
        waiter.wait(StackName=stackName, WaiterConfig={'Delay': 5, 'MaxAttempts': 60})
        print('Successfully deleted stack: %s' % stackName)
    except botocore.exceptions.ClientError as error:
        print("Failed to delete stack %s with error %s" % (
            stackName, error.response['Error']['Message']))


def existing_endpoints(inputJson, session):
    dmsClient = session.client('dms')
    isSourceExisting = False
    existing_source_arn = []
    isTargetExisting = False
    existing_target_arn = []
    isReplicationTaskExisting = False
    # TODO: Handle marker case here
    response = dmsClient.describe_endpoints()
    for eachEndpoint in response['Endpoints']:
        if eachEndpoint['EndpointType'] == 'SOURCE' and (
                ('EngineName' in eachEndpoint and inputJson['SourceEndpointDetails'][
                    'EngineName'] == eachEndpoint['EngineName']) and
                ('ServerName' in eachEndpoint and inputJson['SourceEndpointDetails'][
                    'SourceUrl'] == eachEndpoint['ServerName']) and
                ('Port' in eachEndpoint and inputJson['SourceEndpointDetails']['Port'] ==
                 eachEndpoint['Port']) and
                ('DatabaseName' in eachEndpoint and inputJson['SourceEndpointDetails'][
                    'DatabaseName'] == eachEndpoint['DatabaseName']) and
                ('Status' in eachEndpoint and eachEndpoint['Status'] == 'active')):
            isSourceExisting = True
            existing_source_arn.append(eachEndpoint['EndpointArn'])
        elif eachEndpoint['EndpointType'] == 'TARGET' and (
                ('EngineName' in eachEndpoint and inputJson['TargetEndpointDetails'][
                    'EngineName'] == eachEndpoint['EngineName']) and
                ('ServerName' in eachEndpoint and inputJson['TargetEndpointDetails'][
                    'TargetUrl'] == eachEndpoint['ServerName']) and
                ('Port' in eachEndpoint and inputJson['TargetEndpointDetails']['Port'] ==
                 eachEndpoint['Port']) and
                ('DatabaseName' in eachEndpoint and inputJson['TargetEndpointDetails'][
                    'DatabaseName'] == eachEndpoint['DatabaseName']) and
                ('Status' in eachEndpoint and eachEndpoint['Status'] == 'active')):
            isTargetExisting = True
            existing_target_arn.append(eachEndpoint['EndpointArn'])
    if isSourceExisting and isTargetExisting:
        replicationTasksResponse = dmsClient.describe_replication_tasks(
            Filters=[{'Name': 'endpoint-arn', 'Values': existing_source_arn}])
        for eachTask in replicationTasksResponse['ReplicationTasks']:
            isReplicationTaskExisting = eachTask['SourceEndpointArn'] in existing_source_arn and eachTask[
                'TargetEndpointArn'] in existing_target_arn

    print('isSourceExisting: ' + str(isSourceExisting) + " isTargetExisting: " + str(
        isTargetExisting) + " isReplicationTaskExisting: " + str(isReplicationTaskExisting))

    return isSourceExisting and isTargetExisting and isReplicationTaskExisting


def validate_input_json(inputJson, session):
    if inputJson['TemplateType'] == "NEW_ENDPOINTS":
        schemaFile = read_json_file("../schemas/new-endpoints-template-schema.json", __file__)
    else:
        schemaFile = read_json_file("../schemas/existing-endpoints-template-schema.json", __file__)
    try:
        validate(instance=inputJson, schema=schemaFile)
        if existing_endpoints(inputJson, session):
            raise Exception("Replication task with input Source and Target endpoints exists. Cannot continue")
        else:
            print('Replication task with input source and target endpoints not present. Continue!!!')
    except Exception as e:
        print("Input validation failed with error: " + str(e))
        raise e


def random_string(string_length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(string_length))


def mergeInputFiles(INPUT_PATH):
    final_json = {}
    inputFiles = [f for f in os.listdir(INPUT_PATH) if isfile(join(INPUT_PATH, f))]
    for eachFile in inputFiles:
        if eachFile in ['endpointDetails.json', 'taskDetails.json']:
            with open(os.path.join(INPUT_PATH, eachFile)) as inputFile:
                final_json.update(json.load(inputFile))
    return final_json
