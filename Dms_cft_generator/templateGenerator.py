import copy
import json
import os
import sys
from collections import OrderedDict

BASE_DIR = os.path.abspath(os.getcwd())


def validateInputJson(inputJson):
    return "EXISTING_ENDPOINTS_INPUT"


def createExistingEndpointsReplicationTaskCft(migrationType, replicationInstanceArn, replicationTaskName, tableMapping,
                                              sourceEndpointArn, targetEndpointArn):
    templateJson = copy.deepcopy(EXISTING_ENDPOINTS_TEMPLATE_FILE)
    templateJson['Parameters']['ReplicationInstanceARN']['Default'] = replicationInstanceArn
    templateJson['Parameters']['SourceEndpointARN']['Default'] = sourceEndpointArn
    templateJson['Parameters']['TargetEndpointARN']['Default'] = targetEndpointArn

    templateJson['Resources']['ReplicationTask']['ReplicationTaskIdentifier'] = replicationTaskName
    templateJson['Resources']['ReplicationTask']['MigrationType'] = migrationType
    templateJson['Resources']['ReplicationTask']['TableMappings'] = tableMapping
    return templateJson


def extractReplicationTaskDetailsForExistingEndpointTemplate(inputJson):
    print(inputJson['ReplicationTaskDetails'])
    return [inputJson['ReplicationTaskDetails']['MigrationType'],
            inputJson['ReplicationTaskDetails']['ReplicationInstanceArn'],
            inputJson['ReplicationTaskDetails']['ReplicationTaskIdentifier']]


def extractTableMappingForExistingEndpointTemplate(inputJson):
    return json.dumps(inputJson['TableMappings']).replace('"', '\\"').replace('\n', '\\n')


def extractEndpointDetailsForExistingEndpointTemplates(inputJson):
    return [inputJson['SourceEndpointDetails']['SourceEndpointArn'],
            inputJson['TargetEndpointDetails']['TargetEndpointArn']]


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
                                                                             sourceEndpointArn,
                                                                             targetEndpointArn)
                    outputTemplateFileName = str(eachInputFile.split('.')[0]) + "-cft.json"
                    with open(os.path.join(BASE_DIR, "accounts", eachAccount, "outputs", outputTemplateFileName),
                              'w') as outputFile:
                        json.dump(templateJson, outputFile)
# {
#     "Type": "AWS::DMS::ReplicationTask",
#     "Properties": {
#         "MigrationType": String,
#         "ReplicationInstanceArn": String,
#         "ReplicationTaskIdentifier": String,
#         "SourceEndpointArn": String,
#         "TableMappings": String,
#         "TargetEndpointArn": String,
#     }
# }
