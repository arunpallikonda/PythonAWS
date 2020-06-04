import json
import boto3
import zlib
from base64 import b64decode
import os


def lambda_handler(event, context):
    client = boto3.client('cloudwatch')
    print(event)
    if 'awslogs' in event:
        # decoding the event(which is the log message matching the filter)
        decodedEvent = zlib.decompress(b64decode(event['awslogs']['data']), 16 + zlib.MAX_WBITS).decode("utf-8")
        decodedEventJson = json.loads(decodedEvent)
        replicationTaskName = decodedEventJson["logStream"].split('dms-task-')[1]
        alarmName = 'AWS_fm~DMS~' + replicationTaskName + '~errorLogs'
        metricFilterName = replicationTaskName + '_errorLogs'
        filteredAlarms = client.describe_alarms(
            AlarmNamePrefix=alarmName,
            AlarmTypes=['MetricAlarm'])
        # to check if the alarm is present for the given task
        if len(filteredAlarms['MetricAlarms']) == 0:
            filteredMetrics = listMetrics(client, 'CustomMetric', metricFilterName, replicationTaskName)
            # to check if the metric is present for the given task
            if len(filteredMetrics['Metrics']) == 0:
                # to process if the metric and alarm are not present
                print("Metric and alarm not found. Creating both.")
                # to create metric
                putMetricData(client, 'CustomMetric', metricFilterName, replicationTaskName)
                # to create alarm
                putMetricAlarm(client, alarmName, metricFilterName, 'CustomMetric', replicationTaskName)
                # to trigger alarm
                putMetricData(client, 'CustomMetric', metricFilterName, replicationTaskName)
            else:
                # process if metric is present
                print("Alarm not found. Creating!!!")
                # create alarm
                putMetricAlarm(client, alarmName, metricFilterName, 'CustomMetric', replicationTaskName)
                # trigger alarm
                putMetricData(client, 'CustomMetric', metricFilterName, replicationTaskName)
        else:
            # if metric,alarm  are present
            print("Triggering Alarm!!!")
            # trigger alarm
            putMetricData(client, 'CustomMetric', metricFilterName, replicationTaskName)
    else:
        print("Inside else block")
        client = boto3.client('dms')

        sourceEndpointResponse = client.create_endpoint(
            ServerName='myfirstinstance.cj22o5q92mgn.us-east-1.rds.amazonaws.com',
            EndpointIdentifier='sourceEndpoint',
            EndpointType='source',
            EngineName='mysql',
            Username='admin',
            Password='adminpassword',
            SslMode='none',
            Port=3306
        )
        print("Printing source endpoint response: " + str(sourceEndpointResponse))

        targetEndpointResponse = client.create_endpoint(
            ServerName='mysecondinstance.cj22o5q92mgn.us-east-1.rds.amazonaws.com',
            EndpointIdentifier='targetEndpoint',
            EndpointType='target',
            EngineName='mysql',
            Username='admin',
            Password='adminpassword',
            SslMode='none',
            Port=3306
        )
        print("Printing target endpoint response: " + str(targetEndpointResponse))

        replicationTaskResponse = client.create_replication_task(
            ReplicationTaskIdentifier='MyReplicationTask',
            SourceEndpointArn=sourceEndpointResponse['Endpoint']['EndpointArn'],
            TargetEndpointArn=targetEndpointResponse['Endpoint']['EndpointArn'],
            ReplicationInstanceArn='arn:aws:dms:us-east-1:464420198474:rep:KUM4AINLTPFSSSNHIRXJW6L2AU',
            MigrationType='full-load',
            TableMappings='''{
                "rules": [
                    {
                        "rule-type": "selection",
                        "rule-id": "1",
                        "rule-name": "1",
                        "object-locator": {
                            "schema-name": "Test",
                            "table-name": "%"
                        },
                        "rule-action": "include"
                    }
                ]
            }'''
        )
        print("Printing target endpoint response: " + str(replicationTaskResponse))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello world",
        }),
    }


# method to trigger an alarm
def putMetricData(client, metricNamespace, metricName, replicationTaskName):
    return client.put_metric_data(
        Namespace=metricNamespace,
        MetricData=[
            {
                'MetricName': metricName,
                'Dimensions': [
                    {
                        'Name': 'ReplicationTaskName',
                        'Value': replicationTaskName
                    },
                ],
                'StatisticValues': {
                    'SampleCount': 1.0,
                    'Sum': 1.0,
                    'Minimum': 1.0,
                    'Maximum': 1.0
                },
                'Unit': 'Seconds',
                'StorageResolution': 1
            }])


# method to create an alarm
def putMetricAlarm(client, alarmName, metricName, metricNamespace, replicationTaskName):
    return client.put_metric_alarm(
        AlarmName=alarmName,
        ComparisonOperator='GreaterThanOrEqualToThreshold',
        EvaluationPeriods=1,
        MetricName=metricName,
        Namespace=metricNamespace,
        Period=60,
        Statistic='Sum',
        Threshold=1,
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:sns:us-east-2:464420198474:Default_CloudWatch_Alarms_Topic'
        ],
        Dimensions=[
            {
                'Name': 'ReplicationTaskName',
                'Value': replicationTaskName
            }
        ],
        AlarmDescription='Task alarm')


# method to list the metrics of a given task based on service,namespace and custom metric name
def listMetrics(client, metricNamespace, metricName, replicationTaskName):
    return client.list_metrics(
        Namespace=metricNamespace,
        MetricName=metricName,
        Dimensions=[
            {
                'Name': 'ReplicationTaskName',
                'Value': replicationTaskName
            }])


if __name__ == '__main__':
    fileDir = os.path.dirname(os.path.realpath('__file__'))
    event_file = os.path.join(fileDir, '../events/event.json')
    with open(event_file) as json_file:
        data = json.load(json_file)
        lambda_handler(data, {})
