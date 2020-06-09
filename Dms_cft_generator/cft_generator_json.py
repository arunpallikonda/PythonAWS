import boto3
import json


def skeletonCft(finalCft):
    cftSkeleton = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": 'This CloudFormation sample template for DMSTask and DMS Endpoints Creation.'
                       'A DMS task is created and configured to migrate existing data to the target endpoint.',
        "Parameters": {},
        "Resources": {},
        "Outputs": {}
    }
    finalCft.update(cftSkeleton)


def appendTasks(finalCft):
    with open('task_input.json') as json_file:
        taskInput = json.load(json_file)
        # with open('template_task_input.json') as template_json_file:
        #     templateTaskInput = json.load(template_json_file)
        #     templateTaskInput["MigrationType"]=taskInput["MigrationType"]
        #     write template_json_file to that file again


        # COnstruct and intermediate json
        tempJson = {}
        anotherJson = {}
        anotherJson['Type'] = "AWS::DMS::ReplicationTask"
        anotherJson['Properties'] =
        tempJson['myDMSTask'] = sommething

    "VPC" : {
        "Type" : "AWS::DMS::ReplicationTask",
        "Properties" : {
            "CdcStartPosition" : String,
            "CdcStartTime" : Double,
            "CdcStopPosition" : String,
            "MigrationType" : String,
            "ReplicationInstanceArn" : String,
            "ReplicationTaskIdentifier" : String,
            "ReplicationTaskSettings" : String,
            "SourceEndpointArn" : String,
            "TableMappings" : String,
            "Tags" : [ Tag, ... ],
            "TargetEndpointArn" : String,
            "TaskData" : String
        }
    }

        finalCft['Resources'].update(taskInput)


finalCft = {}
skeletonCft(finalCft)  # step1
print(finalCft)
appendTasks(finalCft)
print(finalCft)
# step2


# {'AWSTemplateFormatVersion': '2010-09-09',
#  'Description': 'This CloudFormation sample template for DMSTask and DMS Endpoints Creation.A DMS task is created and configured to migrate existing data to the target endpoint.',
#  'Parameters': {}, 'Resources': {'ReplicationTask': {'MigrationType': 'full-load',
#                                                      'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:6UTDJGBOUS3VI3SUWA66XFJCJQ',
#                                                      'ReplicationTaskIdentifier': 'dms-auto-task1',
#                                                      'SourceEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:ZW5UAN6P4E77EC7YWHK4RZZ3BE',
#                                                      'TableMappings': 'file://mappingfile.json',
#                                                      'TargetEndpointArn': 'arn:aws:dms:us-east-1:123456789012:endpoint:ASXWXJZLNWNT5HTWCGV2BUJQ7E'}},
#  'Outputs': {}}
#
# {
#     "Type" : "AWS::DMS::ReplicationTask",
#     "Properties" : {
#         "CdcStartPosition" : String,
#         "CdcStartTime" : Double,
#         "CdcStopPosition" : String,
#         "MigrationType" : String,
#         "ReplicationInstanceArn" : String,
#         "ReplicationTaskIdentifier" : String,
#         "ReplicationTaskSettings" : String,
#         "SourceEndpointArn" : String,
#         "TableMappings" : String,
#         "Tags" : [ Tag, ... ],
#         "TargetEndpointArn" : String,
#         "TaskData" : String
#     }
# }

# client = boto3.client('dms')
#
# # def create_dms_task(dms_task_input):
# #     dms_task_response = client.create_replication_task(
# #         ReplicationTaskIdentifier=dms_task_input['ReplicationTask']['ReplicationTaskIdentifier'],
# #         SourceEndpointArn=dms_task_input['ReplicationTask']['SourceEndpointArn'],
# #         TargetEndpointArn=dms_task_input['ReplicationTask']['TargetEndpointArn'],
# #         ReplicationInstanceArn=dms_task_input['ReplicationTask']['ReplicationInstanceArn'],
# #         MigrationType=dms_task_input['ReplicationTask']['MigrationType'],
# #         TableMappings=dms_task_input['ReplicationTask']['TableMappings']
# #     )
#
#
# topLevelJson = {}
#
# with open('task_input.json') as json_file:
#     # validate(json_file)
#     dms_task_input = json.load(json_file)
#     topLevelJson.update(dms_task_input)
#
# with open('endpoints.json') as json_file:
#     endpoint_input_json = json.load(json_file)
#     topLevelJson.update(endpoint_input_json)
#
# with open('topLevelJson.json', 'w') as json_file:
#     json.dump(topLevelJson, json_file)


# dms_endpoint_input_string = {
#     'ReplicationInstance': {
#         'AllocatedStorage': 5,
#         'AutoMinorVersionUpgrade': True,
#         'EngineVersion': '1.5.0',
#         'KmsKeyId': 'arn:aws:kms:us-east-1:123456789012:key/4c1731d6-5435-ed4d-be13-d53411a7cfbd',
#         'PendingModifiedValues': {
#         },
#         'PreferredMaintenanceWindow': 'sun:06:00-sun:14:00',
#         'PubliclyAccessible': True,
#         'ReplicationInstanceArn': 'arn:aws:dms:us-east-1:123456789012:rep:6UTDJGBOUS3VI3SUWA66XFJCJQ',
#         'ReplicationInstanceClass': 'dms.t2.micro',
#         'ReplicationInstanceIdentifier': 'test-rep-1',
#         'ReplicationInstanceStatus': 'creating',
#         'ReplicationSubnetGroup': {
#             'ReplicationSubnetGroupDescription': 'default',
#             'ReplicationSubnetGroupIdentifier': 'default',
#             'SubnetGroupStatus': 'Complete',
#             'Subnets': [
#                 {
#                     'SubnetAvailabilityZone': {
#                         'Name': 'us-east-1d',
#                     },
#                     'SubnetIdentifier': 'subnet-f6dd91af',
#                     'SubnetStatus': 'Active',
#                 },
#                 {
#                     'SubnetAvailabilityZone': {
#                         'Name': 'us-east-1b',
#                     },
#                     'SubnetIdentifier': 'subnet-3605751d',
#                     'SubnetStatus': 'Active',
#                 },
#                 {
#                     'SubnetAvailabilityZone': {
#                         'Name': 'us-east-1c',
#                     },
#                     'SubnetIdentifier': 'subnet-c2daefb5',
#                     'SubnetStatus': 'Active',
#                 },
#                 {
#                     'SubnetAvailabilityZone': {
#                         'Name': 'us-east-1e',
#                     },
#                     'SubnetIdentifier': 'subnet-85e90cb8',
#                     'SubnetStatus': 'Active',
#                 },
#             ],
#             'VpcId': 'vpc-6741a603',
#         },
#     },
#     'ResponseMetadata': {
#         '...': '...',
#     }, }
#
# dms_endpoint_input = json.loads(dms_endpoint_input_string)
#
#
# def create_dms_endpoint():
#     dms_endpoint_response = client.create_endpoint(
#         EndpointIdentifier='string',
#         EndpointType='source',
#         EngineName='string',
#         Username='string',
#         Password='string',
#         ServerName='string',
#         Port=123,
#         DatabaseName='string',
#         ExtraConnectionAttributes='string',
#         KmsKeyId='string',
#         SslMode='none')
