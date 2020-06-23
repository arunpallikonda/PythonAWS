import boto3

from dms_cft_generator.utility.credentials_util import CredentialsUtil
from dms_cft_generator.utility.generic_util import *


def get_appropriate_replication_instance(tags_dict, credentials: CredentialsUtil):
    # TODO: Handle Marker logic
    # TODO: Handle no instance found
    try:
        parsedDict = {}
        for eachDictTag in tags_dict:
            parsedDict[eachDictTag['Key']] = eachDictTag['Value']
        dmsClient = credentials.get_session().client('dms')
        replicationInstanceResponse = dmsClient.describe_replication_instances()
        for replicationInstance in replicationInstanceResponse['ReplicationInstances']:
            tagsResponse = dmsClient.list_tags_for_resource(ResourceArn=replicationInstance['ReplicationInstanceArn'])
            for eachTag in tagsResponse['TagList']:
                if eachTag['Key'] == "AppShortName" and eachTag['Value'] == parsedDict['AppShortName']:
                    return replicationInstance['ReplicationInstanceArn']
                else:
                    return "arn:aws:dms:us-east-1:464420198474:rep:6V4B6NMHFAN3HEDPL6ZODO6VXA"
    except Exception as e:
        print("Failed to get appropriate replication instance with error: " + str(e))
        # Remove this code later on
        print("Using default ReplicationInstance: arn:aws:dms:us-east-1:464420198474:rep:6V4B6NMHFAN3HEDPL6ZODO6VXA")
        return "arn:aws:dms:us-east-1:464420198474:rep:6V4B6NMHFAN3HEDPL6ZODO6VXA"
