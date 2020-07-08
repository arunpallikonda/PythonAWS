import boto3
import botocore.errorfactory
from dms_cft_generator.utility.generic_util import mergeInputFiles

#
# client = boto3.client('dms')
#
# try:
#     response = client.describe_certificates(
#         Filters=[
#             {
#                 'Name': 'certificate-id',
#                 'Values': [
#                     'random'
#                 ]
#             }
#         ]
#     )
#     print(response)
# except botocore.exceptions.ClientError as error:
#     print("cannot find certificate")
#
# # certificate = open('/Users/arun/IdeaProjects/PythonAWS/dms_cft_generator/eros.sso').read()
# #
# # response = client.import_certificate(
# #     CertificateIdentifier='random',
# #     CertificateWallet=certificate
# # )
#
# print(response)

cloudFormationClient = boto3.client('cloudformation')

cloudFormationClient.delete_stack(StackName='dmsauto-bvbyhlnb-task-DMS-stack')
waiter = cloudFormationClient.get_waiter('stack_delete_complete')
waiter.wait(
    StackName='dmsauto-bvbyhlnb-task-DMS-stack',
    WaiterConfig={
        'Delay': 5,
        'MaxAttempts': 60
    }
)
print('Successfully deleted stack: %s' % 'dmsauto-bvbyhlnb-task-DMS-stack')
