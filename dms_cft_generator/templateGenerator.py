import json
import time
import argparse
from os import path

from .utility.credentials_util import CredentialsUtil
from .utility.dms_util import process_existing_endpoints_template, validate_input_json, \
    generate_dms_tags_dict, process_new_endpoints_template, parse_dms_tags_dict


def deploy_cloudformation(templateJson, session, source_db_password):
    cloudFormationClient = session.client('cloudformation')
    dmsClient = session.client('dms')

    replicationTaskIdentifier = templateJson['Resources']['ReplicationTask']['Properties']['ReplicationTaskIdentifier']
    stackName = replicationTaskIdentifier + "-DMS-stack"
    # Create cloud formation stack
    print("Creating stack with password parameter: " + source_db_password)
    response = cloudFormationClient.create_stack(StackName=stackName, TemplateBody=json.dumps(templateJson),
                                                 TimeoutInMinutes=10, Capabilities=['CAPABILITY_IAM'],
                                                 Parameters=[{'ParameterKey': 'PasswordFromPAM',
                                                              'ParameterValue': source_db_password,
                                                              'UsePreviousValue': False}])
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
                # TODO: Delete stack if start replication task failed?
                print("ERROR while starting replication task. Error: " + str(e))
            break
        elif stackStatus == 'CREATE_IN_PROGRESS' or stackStatus == 'UPDATE_IN_PROGRESS':
            print("Stack creation in progress. Sleeping 5secs!!!")
            time.sleep(5)
        else:
            print("Error creating cloudformation stack for replicationTask: " + replicationTaskIdentifier
                  + ". Stack status is " + stackStatus)
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create DMS Replication Task.')
    parser.add_argument('--roleToAssume', action="store", dest="assumeRole", help='ARN of the role to assume',
                        metavar='')
    parser.add_argument('--credentialsProfile', action="store", dest="credentialsProfile",
                        help='AWS Credentials Profile to use', metavar='')
    parser.add_argument('--inputJsonPath', action="store", dest="inputJsonPath", help='Path of the input JSON file',
                        metavar='')
    parser.add_argument('--outputPath', action="store", dest="outputPath", help='Output Path for generated CFT',
                        metavar='')
    parser.add_argument('--environment', action="store", dest="environment", help='Environment to deploy', metavar='')

    ASSUME_ROLE = parser.parse_args().assumeRole
    CREDENTIALS_PROFILE = parser.parse_args().credentialsProfile
    INPUT_JSON_PATH = parser.parse_args().inputJsonPath
    OUTPUT_CFT_PATH = parser.parse_args().outputPath
    ENVIRONMENT = parser.parse_args().environment

    if (not ASSUME_ROLE and not CREDENTIALS_PROFILE) or not INPUT_JSON_PATH or not OUTPUT_CFT_PATH or not ENVIRONMENT:
        raise Exception("Required parameters are not provided. Cannot continue forward.")

    credentials = CredentialsUtil(assume_role=ASSUME_ROLE, credentials_profile=CREDENTIALS_PROFILE, region='us-east-1')

    if path.exists(INPUT_JSON_PATH) and path.isfile(INPUT_JSON_PATH):
        try:
            with open(INPUT_JSON_PATH) as inputFile:
                inputJson = json.load(inputFile)
                tags_dict = generate_dms_tags_dict(app_short_name=inputJson['AppShortName'],
                                                   asset_id=inputJson['AssetId'])
                parsed_tags_dict = parse_dms_tags_dict(tags_dict)
                validate_input_json(inputJson)
                # TODO: Existing endpoints code is not complete
                if inputJson['TemplateType'] == "EXISTING_ENDPOINTS":
                    templateJson = process_existing_endpoints_template(OUTPUT_CFT_PATH, inputJson, tags_dict,
                                                                       parsed_tags_dict, credentials)
                    deploy_cloudformation(templateJson, credentials.get_session(), credentials.get_credentials_from_pam(
                        secret_type='password', app_code=inputJson['AppCode'],
                        db_name=inputJson['SourceEndpointDetails']['DatabaseName'], environment=ENVIRONMENT))
                elif inputJson['TemplateType'] == "NEW_ENDPOINTS":
                    templateJson = process_new_endpoints_template(OUTPUT_CFT_PATH, inputJson, tags_dict,
                                                                  parsed_tags_dict, credentials, ENVIRONMENT)
                    deploy_cloudformation(templateJson, credentials.get_session(), credentials.get_credentials_from_pam(
                        secret_type='password', app_code=inputJson['AppCode'],
                        db_name=inputJson['SourceEndpointDetails']['DatabaseName'], environment=ENVIRONMENT))
                else:
                    print("Invalid templateType: " + inputJson['TemplateType'])
        except Exception as e:
            print("Unable to parse inputFile: " + INPUT_JSON_PATH + ", error: " + str(e))
    else:
        print("Input path is not valid.")
