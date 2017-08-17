import boto3,json,time,os,sys,argparse
from pprint import pprint

DEBUG = False
def get_stream(event):
    profile = None
    region = None
    if 'profile' in event:
        profile = event['profile']
    if 'region' in event:
        region = event['region']
    stop_seqno = -1
    if 'seqno' in event:
        stop_seqno = int(event['seqno'])
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

    #processing the most recent first (same as walking parent backwards)
    shards = sorted(stream['Shards'], key=lambda k: k['SequenceNumberRange'].get('StartingSequenceNumber', 0),reverse=False)
    for shard in shards:
        if 'EndingSequenceNumber' not in shard['SequenceNumberRange']:
            endSeqNo = 0
        else:
            endSeqNo = shard['SequenceNumberRange']['EndingSequenceNumber']
        startSeqNo = shard['SequenceNumberRange']['StartingSequenceNumber']
        shard_id = shard['ShardId']
        if DEBUG: 
            print('SHARD:{}:{}:{}'.format(shard_id,startSeqNo,endSeqNo))
        if stop_seqno > int(startSeqNo):
            if DEBUG: 
                print('End of Sequence Number Range')
            continue

        response = client.get_shard_iterator(
            StreamArn=arn,
            ShardId=shard_id,
            ShardIteratorType='TRIM_HORIZON'
        )
        shard_iter = response['ShardIterator']
        zero_count = 0
        while(True):
            time.sleep(1)
            response = client.get_records(
                ShardIterator=shard_iter,
                Limit=1000
            )
            recs = response['Records']
            if DEBUG: 
                print('{} RECORDS'.format(len(recs)))
            #when end seq no is 0, the stream is open ended and will not end, so try 10 times and stop
            #open ended streams may have records beyond the first response, so we must try multiple times
            if len(recs) == 0:
                zero_count += 1 
            if zero_count > 10:
                break
            for rec in recs:
                eid = rec['eventID']
                en = rec['eventName']
                entry = rec['dynamodb']
                seqno = entry['SequenceNumber']
                ele = None
                if 'NewImage' in entry:
                    ele = entry['NewImage']
                print('{} {}:{}:{}'.format(seqno,en,eid,ele))
                
            if 'NextShardIterator' not in response:
                if DEBUG: 
                    print('END_OF_SHARD_ITERATOR')
                break
            shard_iter = response['NextShardIterator']
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DynamoDB spotFns Table data Parser')
    parser.add_argument('streamARN',action='store',help='DynamoDB table stream ARN')
    parser.add_argument('--profile','-p',action='store',default='cjk1',help='AWS profile to use')
    parser.add_argument('--region','-r',action='store',default='us-west-2',help='AWS region to use')
    parser.add_argument('--seqno',action='store',default=None,help='seq number to start with')
    args = parser.parse_args()
    event = {}
    event['profile'] = args.profile
    event['arn'] = args.streamARN
    event['region'] = args.region
    if args.seqno:
        event['seqno'] = args.seqno
    get_stream(event)

