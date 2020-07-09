import boto3
import botocore.errorfactory

from dms_cft_generator.utility.generic_util import mergeInputFiles

#
client = boto3.client('dms')

try:
    response = client.describe_certificates(
        Filters=[
            {
                'Name': 'certificate-id',
                'Values': [
                    'dmsauto-fsk-sampledb'
                ]
            }
        ]
    )
    print(response['Certificates'][0]['CertificateWallet'])
except botocore.exceptions.ClientError as error:
    print("cannot find certificate")

# certificate = open('/Users/arun/IdeaProjects/PythonAWS/dms_cft_generator/eros.sso').read()
#
# response = client.import_certificate(
#     CertificateIdentifier='random',
#     CertificateWallet=certificate
# )
#
# print(response)

# cloudFormationClient = boto3.client('cloudformation')
#
# cloudFormationClient.delete_stack(StackName='dmsauto-bvbyhlnb-task-DMS-stack')
# waiter = cloudFormationClient.get_waiter('stack_delete_complete')
# waiter.wait(
#     StackName='dmsauto-bvbyhlnb-task-DMS-stack',
#     WaiterConfig={
#         'Delay': 5,
#         'MaxAttempts': 60
#     }
# )
# print('Successfully deleted stack: %s' % 'dmsauto-bvbyhlnb-task-DMS-stack')

# def isYearLeap(year):
#     if year % 100 == 0:
#         if (year % 400) == 0:
#             return True
#         else:
#             return False
#     elif year % 4 == 0:
#         return True
# #     else:
# #         return False
# #
# #
# # def daysInMonth(year, month):
# #     if year:
# #         if month in [1, 3, 5, 7, 8, 10, 12]:
# #             return 31
# #         elif month in [4, 6, 11]:
# #             return 30
# #         elif month == 2:
# #             if isYearLeap(year):
# #                 return 29
# #             else:
# #                 return 28
# # print(daysInMonth(2020, 2))
# #
# # print(isYearLeap(2020))
#
#
# def isYearLeap(year):
#     if year % 100 == 0:
#         if (year % 400) == 0:
#             return True
#         else:
#             return False
#     elif year % 4 == 0:
#         return True
#     else:
#         return False
#
#
# def daysInMonth(year, month):
#     if year:
#         if month in [1, 3, 5, 7, 8, 10, 12]:
#             return 31
#         elif month in [4, 6, 11]:
#             return 30
#         elif month == 2:
#             if isYearLeap(year):
#                 return 29
#             else:
#                 return 28
#
#
# testYears = [1900, 2000, 2016, 1987]
# testMonths = [2, 2, 1, 11]
# testResults = [28, 29, 31, 30]
# for i in range(len(testYears)):
#     yr = testYears[i]
#     mo = testMonths[i]
#     print(yr, mo, "->", end="")
#     result = daysInMonth(yr, mo)
#     if result == testResults[i]:
#         print("OK")
#     else:
#         print("Failed")


line = 'try\n'
line = line.strip('\n')
print(type(line))
