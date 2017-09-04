import boto3
import json, logging, argparse, os, time, uuid

def handler(event, context):
    sns = boto3.client('sns')
    arn = 'arn:aws:sns:us-west-2:443592014519:testtopic'
    subject = 'subject'
    message = 'message{}'.format(str(uuid.uuid4())[:4])
    for i in range(100):
        sns.publish(
            TopicArn=arn,
            Subject=subject,
            Message=message
        )
    return 'done'
