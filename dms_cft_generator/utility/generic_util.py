import json
import os

from jsonschema import validate


def generate_dms_tags_dict(app_short_name, asset_id):
    return [{"Key": "AppShortName", "Value": app_short_name}, {"Key": "AssetId", "Value": asset_id}]


def validate_input_json(inputJson):
    BASE_DIR = os.path.abspath(os.getcwd())
    if inputJson['templateType'] == "NEW_ENDPOINTS":
        schemaFile = json.loads(open(os.path.join(BASE_DIR, "schemas", "new-endpoints-template-schema.json")).read())
    else:
        schemaFile = json.loads(open(os.path.join(BASE_DIR, "schemas", "new-endpoints-template-schema.json")).read())

    try:
        validate(instance=inputJson, schema=schemaFile)
    except Exception as e:
        print("Input validation failed with error: " + str(e))
        raise e
