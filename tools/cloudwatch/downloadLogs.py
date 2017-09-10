'''
    author: Chandra Krintz
    Download cloudwatch logs, delete from AWS once downloaded
    LICENSE: https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/blob/master/LICENSE
'''
import boto3,argparse,sys,time
from pprint import pprint
from datetime import datetime

############ find_streams ##################
def find_streams(logs,log_group,token,start,end):
    def valid_stream(stream):
        cts = stream['creationTime'] 
        if 'lastEventTimestamp' not in stream:
            return False
        lets = stream['lastEventTimestamp'] 
        return cts >= start and lets <= end 

    data = None
    #print('Processing {}...'.format(log_group))
    try:
        if token:
            data = logs.describe_log_streams(logGroupName=log_group, nextToken=token)
        else:
            data = logs.describe_log_streams(logGroupName=log_group)
    except:
        pass

    if not data: #data will be None upon exception above
        print('No streams found for log group {}'.format(log_group))
        return None
    streams = list(filter(valid_stream, data['logStreams']))
    if len(streams) > 0 or 'nextToken' not in data:
        return streams

    time.sleep(0.5) # rate limiting
    return find_streams(logs, log_group, data['nextToken'], start,end)


############ process_msg  ##################
def process_msg(msg):
    ''' returns a string of 2 (spotwrap tool) 3(report) or 4 (spotwrap) delimited(:) items
    '''
    if 'SpotWrap' in msg: #spotwrap entry
        m = msg.split('\t')
        reqid = m[2]
        m = m[3].split(':')
        duration = float(m[5])
        duration_call = float(m[7])
        status = float(m[9])
        #Fn:reqID:duration_measured_for_this_fn:status_reported_by_call
        retn = '{}:{}:{}:{}'.format(reqid,duration,duration_call,status)
    elif 'TIMER' in msg: #spotwrap app entry
        m = msg.split('\t')
        reqid = m[2]
        if 'INVOKE' in msg: #spotwrap invoker app entry
            m = m[3].split(':')
            if len(m) == 5: #SpotTemplatePy
                duration_call = float(m[4])
                duration = float(m[2])
            else :
                assert len(m) == 16 #FnInvokerPy
                duration_call = float(m[12])
                duration = float(m[15])
            status=202
            #Fn:reqID:duration_measured_for_this_fn:duration_measured_for_invoke:status=202
            retn = '{}:{}:{}:{}'.format(reqid,duration,duration_call,status)
        else:
            m = m[3].split(':')
            if 'SpotTemplatePy' in msg or 'GammaWrapPython' in msg:
                duration = float(m[5])
            elif m[0].startswith('No_context'): #FnInvoker
                duration = float(m[13])
            else: 
                duration = float(m[2])
            retn = '{}:{}'.format(reqid,duration)
    else: #Cloudwatch Report entry
        print(msg)
        assert 'REPORT' in msg
        m = msg.split(' ')
        reqid = m[2].split('\t')[0]
        duration = float(m[3])
        mem = float(m[14])
        retn = '{}:{}:{}'.format(reqid,duration,mem) #Fn:reqID:duration_billed:mem_used
    return retn        

############ find_events ##################
def find_events(logs, log_group, stream, token, last_token, start,end, noSummarize=False):
    def valid_event(event):
        msg = event['message']
        #return (msg.startswith('REPORT') or msg.find('TIMER:') or msg.startswith('UDP') != -1)
        return (msg.startswith('REPORT') or msg.find('TIMER:') != -1)

    if token:
        data = logs.get_log_events(logGroupName=log_group, logStreamName=stream, startFromHead=True, nextToken=token)
    else: 
        data = logs.get_log_events(logGroupName=log_group, logStreamName=stream, startFromHead=True)

    for event in list(filter(valid_event, data['events'])):
        msg = event['message'].strip()
        print(msg)
        if not noSummarize:
            msg = process_msg(msg)
        print('{}:{}'.format(log_group,msg))

    if data['nextForwardToken'] != last_token:
        time.sleep(0.5) # rate limiting
        find_events(logs, log_group, stream, data['nextForwardToken'], token, start,end)

############ main ##################
def main():
    # parse args
    parser = argparse.ArgumentParser(description="AWS Cloudwatch Download and Delete Script")
    parser.add_argument('logGroup',action='store',help='Cloudwatch log group (multiple groups OK if separated by commas with entire list in double quotes')
    parser.add_argument('startTs',action='store',help='Filter streams where creationTime is no earlier than this *UTC/GMT* value (value expected in UTC epoch millisecs, else use the --useString option for datetime UTC string in %Y-%m-%d %H:%M:%S format)')
    parser.add_argument('--endTs',action='store',default=None,help='Filter streams where creationTime is not after this value. default = now, value must be UTC epoch millisecs, else use the --useString option for datetime UTC string in %Y-%m-%d %H:%M:%S format)')
    parser.add_argument("--useString",default=False, help="Use string datetime for start and end instead of epoch milliseconds")
    parser.add_argument("--noSummarize",action='store_true',default=False, help="don't summarize, just dump everything")
    parser.add_argument("--profile","-p",default=None, help="AWS credentials file profile to use.")
    parser.add_argument('--region','-r',action='store',default='us-west-2',help='AWS Region log is in')
    parser.add_argument('--delete',action='store_true',default=False,help='Delete streams once downloaded')
    parser.add_argument('--deleteOnly',action='store_true',default=False,help='Delete streams once downloaded')
    args = parser.parse_args()
    profile = args.profile
    aws_region = args.region
    log_group = args.logGroup
    if args.useString:
        start = int(datetime.strptime(args.startTs, '%Y-%m-%d %H:%M:%S').strftime('%s')) * 1000
        if not args.endTs:
            e = datetime.now()
            end = int(e.timestamp*1000)
        else: 
            e = args.endTs
            end = int(datetime.strptime(e, '%Y-%m-%d %H:%M:%S').strftime('%s')) * 1000
    else:
        start = int(args.startTs)
        if not args.endTs:
            e = datetime.now()
            end = int(e.timestamp()*1000)
        else:
            end = int(args.endTs)
    assert end >= start

    #setup AWS handler
    if profile:
        boto3.setup_default_session(profile_name=profile)
    logs = boto3.client('logs', region_name=aws_region)

    full_streams = find_streams(logs,log_group,None,start,end)
    if full_streams:
        streams = [stream['logStreamName'] for stream in full_streams]
        for stream in streams:
            if not args.deleteOnly:
                find_events(logs, log_group, stream, None, None, start,end,args.noSummarize)
            if args.delete or args.deleteOnly:
                logs.delete_log_stream(logGroupName=log_group,logStreamName=stream)

if __name__ == "__main__":
    main()
