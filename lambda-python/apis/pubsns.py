import boto3
import json, logging, argparse, os, time

def handler(event, context):
    sns = boto3.client('sns')
    arn = 'arn:aws:sns:us-west-2:185174815983:swtest'
    subject = 'subject'
    message = 'message'
    for i in range(100):
        sns.publish(
            TopicArn=arn,
            Subject=subject,
            Message=message
        )
    return 'done'