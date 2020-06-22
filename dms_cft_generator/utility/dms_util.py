import boto3

from dms_cft_generator.utility.credentials_util import CredentialsUtil
from dms_cft_generator.utility.generic_util import *


def get_appropriate_replication_instance(tags_dict, credentials: CredentialsUtil):
    # TODO: Handle Marker logic
    # TODO: Handle no instance found
    dmsClient = credentials.get_session().client('dms')
    replicationInstanceResponse = dmsClient.describe_replication_instances()
    for replicationInstance in replicationInstanceResponse['ReplicationInstances']:
        tagsResponse = dmsClient.list_tags_for_resource(ResourceArn=replicationInstance['ReplicationInstanceArn'])
        for eachTag in tagsResponse['TagList']:
            if eachTag['Key'] == "AppShortName" and eachTag['Value'] == tags_dict['AppShortName']:
                return replicationInstance['ReplicationInstanceArn']

# print(get_appropriate_replication_instance(generate_dms_tags_dict("fsk", "2217"), CredentialsUtil()))
