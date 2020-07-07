import boto3
import botocore.errorfactory

client = boto3.client('dms')

try:
    response = client.describe_certificates(
        Filters=[
            {
                'Name': 'certificate-id',
                'Values': [
                    'random'
                ]
            }
        ]
    )
    print(response)
except botocore.exceptions.ClientError as error:
    print("cannot find certificate")

# certificate = open('/Users/arun/IdeaProjects/PythonAWS/dms_cft_generator/eros.sso').read()
#
# response = client.import_certificate(
#     CertificateIdentifier='random',
#     CertificateWallet=certificate
# )

print(response)
