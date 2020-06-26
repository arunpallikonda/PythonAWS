import json
import os
import string
import random

from jsonschema import validate


def read_json_file(path, file):
    current_path = os.path.abspath((os.path.dirname(file)))
    return json.loads(open(os.path.join(current_path, path)).read())


def validate_input_json(inputJson):
    if inputJson['TemplateType'] == "NEW_ENDPOINTS":
        schemaFile = read_json_file("../schemas/new-endpoints-template-schema.json", __file__)
    else:
        schemaFile = read_json_file("../schemas/existing-endpoints-template-schema.json", __file__)
    try:
        validate(instance=inputJson, schema=schemaFile)
    except Exception as e:
        print("Input validation failed with error: " + str(e))
        raise e


def random_string(string_length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(string_length))
