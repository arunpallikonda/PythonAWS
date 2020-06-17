import boto3


class DmsUtil:
    def __init__(self):
        self.session = boto3.Session()

    def is_existing_endpoint(self, endpoint_identifier):
        response = self.dmsClient.describe_endpoints(
            Filters=[{'Name': 'EndpointIdentifier', 'Values': [endpoint_identifier]}])
        return response

    def getSession(self, **kwargs):
        ASSUME_ROLE = kwargs.get('assume_role', None)
        REGION = kwargs.get('region', None)
        self.session = boto3.Session(region_name=REGION)

        if ASSUME_ROLE:
            print("Assuming role " + ASSUME_ROLE + " for credentials")
            stsConnection = boto3.client('sts')
            stsCredentials = stsConnection.assume_role(RoleArn=ASSUME_ROLE, RoleSessionName="dmsauto-assume-role")
            ACCESS_KEY = stsCredentials['Credentials']['AccessKeyId']
            SECRET_KEY = stsCredentials['Credentials']['SecretAccessKey']
            SESSION_TOKEN = stsCredentials['Credentials']['SessionToken']

            self.session = boto3.session.Session(aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY,
                                                 aws_session_token=SESSION_TOKEN, region_name=REGION)
        return self.session


dms_util = DmsUtil()

print(dms_util.getSession().client('sts').get_caller_identity())
