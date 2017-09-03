import boto3
import random

def handler(event, context):
    s3_client = boto3.client('s3')
    for i in range(100):
        key = str(random.randint(1, 1000)) + '/file'
        response = s3_client.get_object(Bucket='spotwraptest0831',Key=key)
        contents = response['Body'].read()
    return 'done'