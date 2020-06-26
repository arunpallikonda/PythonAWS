import os
import boto3
import subprocess


class CredentialsUtil:
    def __init__(self, **kwargs):
        ASSUME_ROLE = kwargs.get('assume_role', None)
        CREDENTIALS_PROFILE = kwargs.get('credentials_profile', None)
        REGION = kwargs.get('region', None)

        if CREDENTIALS_PROFILE:
            self.session = boto3.session.Session(profile_name=CREDENTIALS_PROFILE)
        elif ASSUME_ROLE:
            print("Assuming role " + ASSUME_ROLE + " for credentials")
            stsConnection = boto3.client('sts')
            stsCredentials = stsConnection.assume_role(RoleArn=ASSUME_ROLE, RoleSessionName="dmsauto-assume-role")
            ACCESS_KEY = stsCredentials['Credentials']['AccessKeyId']
            SECRET_KEY = stsCredentials['Credentials']['SecretAccessKey']
            SESSION_TOKEN = stsCredentials['Credentials']['SessionToken']

            self.session = boto3.session.Session(aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY,
                                                 aws_session_token=SESSION_TOKEN, region_name=REGION)
        else:
            self.session = boto3.Session(region_name=REGION)

    def get_session(self):
        return self.session

    def get_credentials_from_secrets_manager(self, secret_type, inputJson, parsed_tags_dict, environment):
        # TODO: change how we build the string
        secret_name = "/" + parsed_tags_dict['ApplicationShortName'] + "/" + inputJson['TargetEndpointDetails'][
            'RDSInstanceIdentifier'] + "-" + parsed_tags_dict['ApplicationShortName'] + "_dbo" + environment
        if secret_type == "username":
            return "{{resolve:secretsmanager:" + secret_name + ":SecretString:username}}"
        elif secret_type == "password":
            return "{{resolve:secretsmanager:" + secret_name + ":SecretString:password}}"

    def get_credentials_from_pam(self, secret_type, app_code, db_name, environment):
        print("Retrieving credentials from PAM")
        print("Set app code as " + app_code)
        os.environ["APP_CD"] = app_code
        print("Set environment code as " + environment)

        os.environ["ENV_CD"] = environment
        if secret_type == "password":
            # TODO: Change this hardcoded one
            secret_name = "BB9_ORACLE_AWSDMS_" + db_name + "_ACCT"
            # TODO: Remove this try except sending dummyValue
            try:
                return subprocess.check_output("/export/apps/epv/evas/capi/evascli GetPassword " + secret_name,
                                               shell=True)
            except Exception as e:
                print("Unable to retrieve password from PAM. Returning default value")
                return "dummyValue"
        elif secret_type == "username":
            return "dms_" + app_code
