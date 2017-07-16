import boto3
from datetime import datetime
import json, logging, jsonpickle

def handler(event, context):
    start = datetime.now()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if context:
        serialized = jsonpickle.encode(context)
        logger.info('dbMod.handler context: {}'.format(json.loads(serialized)))
    key = 'from:dbMod' #won't trigger function b/c no write if already in table
    val = 17
    if event:
        serialized = jsonpickle.encode(event)
        logger.info('dbMod.handler context: {}'.format(json.loads(serialized)))
        if 'mykey' in event:
            key = event['mykey']
        if 'myval' in event:
            val = event['myval']
        if 'functionName' in event:
            caller = event['functionName']

    if context:
        logger.info('dbMod.handler: writing to dynamodb')
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
        table = dynamodb.Table('triggerTable')
        table.put_item( Item={
            'name': key,
            'age': val,
            }
        )

    delta = datetime.now()-start
    ms = int(delta.total_seconds() * 1000)
    me_str = 'TIMER:CALL:0:HANDLER:{}'.format(ms)
    logger.info(me_str)
    return me_str
