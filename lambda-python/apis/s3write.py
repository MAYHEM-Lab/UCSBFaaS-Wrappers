import boto3
import random

def handler(event, context):
    s3 = boto3.resource('s3')
    for i in range(100):
        key = 'write/' + str(random.randint(1, 1000)) + '/file'
        s3.Bucket('spotwraptest0831').put_object(Key=key, Body='')
    return 'done'