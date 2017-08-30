#from fleece import boto3
import boto3
from fleece.xray import (monkey_patch_botocore_for_xray,
                         trace_xray_subsegment)
import json, logging, argparse, time, jsonpickle, os

monkey_patch_botocore_for_xray()

def detect_labels(bucket, key, max_labels=10, min_confidence=90, region="us-west-2"):
	rekognition = boto3.client("rekognition", region)
	response = rekognition.detect_labels(
		Image={
			"S3Object": {
				"Bucket": bucket,
				"Name": key,
			}
		},
		MaxLabels=max_labels,
		MinConfidence=min_confidence,
	)
	return response['Labels']

def handler(event, context):
    entry = time.time() * 1000
    logger = logging.getLogger()
    reg = 'us-west-2'
    tablename = 'imageLabels'
    if event:
        if 'region' in event:
            reg = event['region']
        if 'tableName' in event:
            tablename = event['tableName']
    if not context: #calling from main so set the profile we want
        session = boto3.Session(profile_name='cjk1')
        s3_client = session.resource('s3')
        dynamodb = session.resource('dynamodb', region_name=reg)
    else:
        s3_client = boto3.resource('s3')
        dynamodb = boto3.resource('dynamodb', region_name=reg)

    bktname = None
    key = None
    if context:
        serialized = jsonpickle.encode(context)
        logger.warn('context: {}'.format(json.loads(serialized)))
    if event:
        serialized = jsonpickle.encode(event)
        logger.warn('event: {}'.format(json.loads(serialized)))
            #s3 event: {'Records': [{'awsRegion': 'us-west-2', 'eventName': 'ObjectCreated:Put', 'eventSource': 'aws:s3', 'eventTime': '2017-08-30T20:30:35.581Z', 'eventVersion': '2.0', 'requestParameters': {'sourceIPAddress': '98.171.178.234'}, 'responseElements': {'x-amz-id-2': 'xw4/vqjUwiRLOXwqRNAsSBiPcd72QamenQnDI/2sm/IYXm+72A1S+TQIJYjAv2oyiq3TsY6SuYQ=', 'x-amz-request-id': '4D69F866BA76CA70'}, 's3': {'bucket': {'arn': 'arn:aws:s3:::cjktestbkt', 'name': 'cjktestbkt', 'ownerIdentity': {'principalId': 'A13UVRJM0LZTMZ'}}, 'configurationId': '3debbff2-99b6-48d0-92df-6fba9b5ddda5', 'object': {'eTag': '9f2e3e584c7c8ee4866669e2d1694703', 'key': 'imgProc/deer.jpg', 'sequencer': '0059A7206B7A3C594C', 'size': 392689}, 's3SchemaVersion': '1.0'}, 'userIdentity': {'principalId': 'AWS:AIDAJQRLZF5NITGU76JME'}}]}
        if 'Records' in event:
            recs = event['Records']
            obj = recs[0]
            if 'eventSource' in obj and 'aws:s3' in obj['eventSource']:
                #s3 triggered
                assert 's3' in obj
                s3obj = obj['s3']
                assert 'bucket' in s3obj
                bkt = s3obj['bucket']
                assert 'name' in bkt
                bktname = bkt['name']
                assert 'object' in s3obj
                keyobj = s3obj['object']
                assert 'key' in keyobj
                key = keyobj['key']
        elif 'eventSource' in event and 'ext:invokeCLI' in event['eventSource']:
            #fninvoke event: {'bkt': 'cjktestbkt', 'eventSource': 'ext:invokeCLI', 'name': 'prefix/test.jpg'}
            assert 'name' in event
            bktname = event['name']
            assert 'key' in event
            key = event['key']

    assert bktname is not None and key is not None
    labels = detect_labels(bktname, key)
    #for label in labels:
        #[{'Name': 'Animal', 'Confidence': 96.52118682861328},...]
        #print('{}:{}'.format(label['Name'],label['Confidence']))

    table = dynamodb.Table(tablename) # we assume key is id of type String
    table.put_item( Item={
        'id': key,
        'labels': json.dumps(labels)
        }
    )

    delta = (time.time() * 1000) - entry
    me_str = 'TIMER:CALL:{}'.format(delta)
    logger.warn(me_str)
    return me_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='s3Mod Test')
    # for this table, we assume key is name of type String
    parser.add_argument('bkt',action='store',help='s3 bkt name')
    parser.add_argument('prefix',action='store',help='fname prefix')
    parser.add_argument('fname',action='store',help='fname')
    args = parser.parse_args()
    event = {'eventSource':'ext:invokeCLI','name':args.bkt,'key':'{}/{}'.format(args.prefix,args.fname)}
    handler(event,None)
