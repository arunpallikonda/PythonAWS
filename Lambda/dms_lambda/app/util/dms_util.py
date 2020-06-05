import boto3


class DmsUtil:
    def __init__(self):
        self.dmsClient = boto3.resource("dms")

    def is_existing_endpoint(self, endpoint_identifier):
        response = self.dmsClient.describe_endpoints(Filters=[{'Name': 'EndpointIdentifier', 'Values': [endpoint_identifier]}])
        return response
