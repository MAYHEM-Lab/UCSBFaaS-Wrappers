import boto3, os
import time
import json, logging, jsonpickle, argparse

def handler(event, context):
    logger = logging.getLogger()
    if context:
        serialized = jsonpickle.encode(context)
        logger.warn('dbMod.handler context: {}'.format(json.loads(serialized)))
        if event:
            serialized = jsonpickle.encode(event)
            logger.warn('dbMod.handler event: {}'.format(json.loads(serialized)))
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
    else: #calling from main (testing)
        session = boto3.Session(profile_name='cjk1') #replace with your profile
        dynamodb = session.resource('dynamodb', region_name='us-west-2')
    tablename = 'triggerTable'
    key = 'from:dbMod' #won't trigger function b/c no write if already in table
    val = 17
    if event:
        if 'mykey' in event:
            key = event['mykey']
        if 'myval' in event:
            val = event['myval']
        if 'functionName' in event:
            caller = event['functionName']
        if 'tablename' in event:
            tablename = event['tablename']
    table = dynamodb.Table(tablename) # we assume key is name of type String
    #read it
    item = table.get_item( Key={'name': key})
    #write it
    table.put_item( Item={
        'name': key,
        'age': val,
        }
    )

    ms = int(round(time.time() * 1000))
    me_str = 'TIMER:CALL:0:HANDLER:{}'.format(ms)
    logger.warn(me_str)
    return me_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='dbMod Test')
    # for this table, we assume key is name of type String
    parser.add_argument('tablename',action='store',help='dynamodb table name')
    parser.add_argument('mykey',action='store',help='key')
    parser.add_argument('myval',action='store',help='value')
    args = parser.parse_args()
    event = {'tablename':args.tablename,'mykey':args.mykey,'myval':args.myval}
    handler(event,None)
