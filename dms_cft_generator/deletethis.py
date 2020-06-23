import boto3
import jsonschema
import json
import os


from jsonschema import validate

BASE_DIR = os.path.abspath(os.getcwd())
schemaFile = json.loads(open(os.path.join(BASE_DIR, "schemas", "new-endpoints-template-schema.json")).read())
jsonData = json.loads(open(os.path.join(BASE_DIR, "accounts", "lab", "inputs", "third.json")).read())

try:
    validate(instance=jsonData, schema=schemaFile)
except Exception as e:
    print(e)
    print("Something wrong cannot move forward")
