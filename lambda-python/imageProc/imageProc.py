import boto3, json, logging, argparse, time, jsonpickle, os, uuid
from fleece.xray import (monkey_patch_botocore_for_xray,
                         monkey_patch_requests_for_xray,
                         trace_xray_subsegment)

monkey_patch_botocore_for_xray()
monkey_patch_requests_for_xray()

'''Setup
cd imageProc
deactivate
virtualenv fleece_venv --python=python3
source fleece_env/bin/activate
pip install fleece jsonpickle
cd ..
python setupApps.py -f setupIProc.json --no_spotwrap --turn_on_tracing --profile aws_profile

//go to DynamoDB Management Console and create table imageLables with key "id" of type string
//create a table triggerTable with key "name" of type string

//go to s3 Management Console and create bucket MYBKTNAME
//create a folder called imgProc and place any image (filename.jpg) in this folder
test locally via: python imageProc/imageProc.py MYBKTNAME imgProc filename.jpg

//go to Lambda Management Console for
//ImageProcPy, Triggers tab, add Trigger, S3, choose bucket MYBKTNAME, 
//prefix: imgProc, enable trigger
test as function via:
aws lambda invoke --invocation-type Event --function-name ImageProcPy --region us-west-2 --profile aws_profile --payload '{"eventSource":"ext:invokeCLI","name":"MYBKTNAME","key":"imgProc/filname.jpg"}' outputfile

test as triggered function by dropping another file into MYBKTNAME/imageProc/ folder.
See entry in DynamoDB table imageLabels
See entry in DynamoDB table triggerTable (make this table trigger a different function)
View X-Ray service graph (there will be two "applications" with separate "clients" without GammaRay support)

'''

def detect_labels(rekog, bucket, key, max_labels=10, min_confidence=90, region="us-west-2"):
    try:
        response = rekog.detect_labels(
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
    except:
        print("Unable to find bucket {} or key {}.  Please retry.".format(bucket,key))
        return None

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
        boto3.setup_default_session(profile_name='cjk1')
        session = boto3.Session(profile_name='cjk1')
        dynamodb = session.resource('dynamodb', region_name=reg)
        rekog = boto3.client("rekognition", reg)

    else: #function triggered
        dynamodb = boto3.resource('dynamodb', region_name=reg)
        rekog = boto3.client("rekognition", reg)

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
    labels = detect_labels(rekog, bktname, key)
    #for label in labels:
        #[{'Name': 'Animal', 'Confidence': 96.52118682861328},...]
        #print('{}:{}'.format(label['Name'],label['Confidence']))

    table = dynamodb.Table(tablename) # we assume key is id of type String
    table.put_item( Item={
        'id': key,
        'labels': json.dumps(labels)
        }
    )
    table = dynamodb.Table('triggerTable') # we assume key is id of type String
    key = str(uuid.uuid4())[:4]
    val = 17
    table.put_item( Item={
        'name': key,
        'age': val,
        }
    )

    delta = (time.time() * 1000) - entry
    me_str = 'TIMER:CALL:{}'.format(delta)
    logger.warn(me_str)
    return me_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='imageProc tool')
    # for this table, we assume key is name of type String
    parser.add_argument('bkt',action='store',help='s3 bkt name')
    parser.add_argument('prefix',action='store',help='fname prefix')
    parser.add_argument('fname',action='store',help='fname')
    args = parser.parse_args()
    event = {'eventSource':'ext:invokeCLI','name':args.bkt,'key':'{}/{}'.format(args.prefix,args.fname)}
    handler(event,None)
