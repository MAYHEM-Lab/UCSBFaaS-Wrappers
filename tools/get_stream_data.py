import boto3,json,time,os,sys,argparse
from pprint import pprint

DEBUG = True
def get_stream(event):
    profile = None
    region = None
    if 'profile' in event:
        profile = event['profile']
    if 'region' in event:
        region = event['region']
    if 'arn' in event:
        arn = event['arn']
    else: 
        print('Error, no arn specified')
        sys.exit(1)
    
    if profile:
        boto3.setup_default_session(profile_name=profile)

    client = boto3.client('dynamodbstreams', region_name=region)
    stream = client.describe_stream(
        StreamArn=arn,
        Limit=100 #use max
    )['StreamDescription']

    shards = sorted(stream['Shards'], key=lambda k: k['SequenceNumberRange'].get('StartingSequenceNumber', 0),reverse=True)
    for shard in shards:
        if 'EndingSequenceNumber' not in shard['SequenceNumberRange']:
            endSeqNo = 0
        else:
            endSeqNo = shard['SequenceNumberRange']['EndingSequenceNumber']
        startSeqNo = shard['SequenceNumberRange']['StartingSequenceNumber']
        shard_id = shard['ShardId']
        print('SHARD:{}:{}:{}'.format(shard_id,startSeqNo,endSeqNo))
        response = client.get_shard_iterator(
            StreamArn=arn,
            ShardId=shard_id,
            ShardIteratorType='TRIM_HORIZON'
            #SequenceNumber='12570400000000014960948147'
        )
        shard_iter = response['ShardIterator']
        while(True):
            time.sleep(1)
            response = client.get_records(
                ShardIterator=shard_iter,
                Limit=1000
            )
            recs = response['Records']
            for rec in recs:
                eid = rec['eventID']
                en = rec['eventName']
                entry = rec['dynamodb']
                seqno = entry['SequenceNumber']
                ele = None
                if 'NewImage' in entry:
                    ele = entry['NewImage']
                print('{}:{}:{}:{}'.format(seqno,en,eid,ele))
                
            if 'NextShardIterator' not in response:
                print('END_OF_SHARD_ITERATOR')
                break
            shard_iter = response['NextShardIterator']
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DynamoDB spotFns Table data Parser')
    parser.add_argument('streamARN',action='store',help='DynamoDB table stream ARN')
    parser.add_argument('--profile','-p',action='store',default='cjk1',help='AWS profile to use')
    parser.add_argument('--region','-r',action='store',default='us-west-2',help='AWS region to use')
    args = parser.parse_args()
    event = {}
    event['profile'] = args.profile
    event['arn'] = args.streamARN
    event['region'] = args.region
    get_stream(event)

