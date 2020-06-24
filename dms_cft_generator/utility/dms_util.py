import copy

from .credentials_util import CredentialsUtil
from .generic_util import *


def generate_dms_tags_dict(app_short_name, asset_id):
    return [{"Key": "AppShortName", "Value": app_short_name}, {"Key": "AssetId", "Value": asset_id}]


def parse_dms_tags_dict(tags_dict):
    parsed_dict = {}
    for eachDictTag in tags_dict:
        parsed_dict[eachDictTag['Key']] = eachDictTag['Value']
    return parsed_dict


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


def updateSourceEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials, tags_dict,
                                                      parsed_tags_dict, environment):
    templateJson['Resources']['SourceEndpoint']['Properties']['ServerName'] = inputJson['SourceEndpointDetails'][
        'SourceUrl']
    templateJson['Resources']['SourceEndpoint']['Properties']['EndpointIdentifier'] = \
        inputJson['SourceEndpointDetails']['EndpointIdentifier']
    templateJson['Resources']['SourceEndpoint']['Properties']['EndpointType'] = "source"
    templateJson['Resources']['SourceEndpoint']['Properties']['EngineName'] = inputJson['SourceEndpointDetails'][
        'EngineName']
    templateJson['Resources']['SourceEndpoint']['Properties']['Port'] = inputJson['SourceEndpointDetails']['Port']
    templateJson['Resources']['SourceEndpoint']['Properties']['Username'] = credentials.get_credentials_from_pam(
        secret_type='username', app_code=inputJson['AppCode'],
        db_name=inputJson['SourceEndpointDetails']['DatabaseName'], environment=environment)
    templateJson['Resources']['SourceEndpoint']['Properties']['DatabaseName'] = inputJson['SourceEndpointDetails'][
        'DatabaseName']
    templateJson['Resources']['SourceEndpoint']['Properties']['Tags'] = tags_dict


def updateTargetEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials, tags_dict,
                                                      parsed_tags_dict, environment):
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
        'Username'] = credentials.get_credentials_from_secrets_manager(secret_type='username',
                                                                       inputJson=inputJson, environment=environment,
                                                                       parsed_tags_dict=parsed_tags_dict)
    templateJson['Resources']['TargetEndpoint']['Properties'][
        'Password'] = credentials.get_credentials_from_secrets_manager(secret_type='password',
                                                                       inputJson=inputJson, environment=environment,
                                                                       parsed_tags_dict=parsed_tags_dict, )
    templateJson['Resources']['TargetEndpoint']['Properties']['DatabaseName'] = inputJson['TargetEndpointDetails'][
        'DatabaseName']
    templateJson['Resources']['TargetEndpoint']['Properties']['Tags'] = tags_dict


def process_existing_endpoints_template(OUTPUT_CFT_PATH, inputJson, tags_dict, parsed_tags_dict, credentials):
    EXISTING_ENDPOINTS_TEMPLATE_FILE = json.loads(
        open(os.path.join("..", "templates", "dms-task-existing-endpoints-template.json")).read())
    templateJson = copy.deepcopy(EXISTING_ENDPOINTS_TEMPLATE_FILE)
    updateReplicationTaskDetailsInTemplate(inputJson, templateJson, tags_dict, credentials)
    updateTableMappingInTemplate(inputJson, templateJson)
    updateEndpointDetailsInExistingEndpointsTemplate(inputJson, templateJson)

    outputTemplateFileName = templateJson['Resources']['ReplicationTask']['Properties'][
                                 'ReplicationTaskIdentifier'] + "-cft.json"
    with open(os.path.join(OUTPUT_CFT_PATH, outputTemplateFileName), 'w') as outputFile:
        json.dump(templateJson, outputFile, indent=4)
    return templateJson


def process_new_endpoints_template(OUTPUT_CFT_PATH, inputJson, tags_dict, parsed_tags_dict, credentials, environment):
    NEW_ENDPOINTS_TEMPLATE_FILE = read_json_file(path="../templates/dms-task-new-endpoints-template.json",
                                                 file=__file__)
    templateJson = copy.deepcopy(NEW_ENDPOINTS_TEMPLATE_FILE)
    updateReplicationTaskDetailsInTemplate(inputJson, templateJson, tags_dict, credentials)
    updateTableMappingInTemplate(inputJson, templateJson)
    updateSourceEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials, tags_dict, parsed_tags_dict,
                                                      environment)
    updateTargetEndpointDetailsInNewEndpointsTemplate(inputJson, templateJson, credentials, tags_dict, parsed_tags_dict,
                                                      environment)

    outputTemplateFileName = templateJson['Resources']['ReplicationTask']['Properties'][
                                 'ReplicationTaskIdentifier'] + "-cft.json"
    with open(os.path.join(OUTPUT_CFT_PATH, outputTemplateFileName), 'w') as outputFile:
        json.dump(templateJson, outputFile, indent=4)
    return templateJson
