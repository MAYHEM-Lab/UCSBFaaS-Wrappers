import boto3
import json, logging, time, argparse

def handler(event,context):
    entry = time.time() * 1000
    logger = logging.getLogger()
    #hard code it in case its not available in the context for some reason
    me = 'unknown'
    reqID = 'unknown'
    if not context: #invoking from main
        boto3.setup_default_session(profile_name='cjk1')
    else:
        me = context.invoked_function_arn
        reqID = context.aws_request_id
    lambda_client = boto3.client('lambda')

    fn = None
    count = 1
    if event:
        if 'functionName' in event:
            fn = event['functionName']
        if 'count' in event:
            count = int(event['count'])

    #run_lambda does not support invoke via Payload arg
    invoke_response = None
    if fn and fn != me:
        msg = {}
        now = time.time() * 1000
        msg['msg'] = 'from {} at {}'.format(me,now)
        msg['requestId'] = reqID
        if event and 'eventSource' in event and me == 'unknown': 
            msg['eventSource'] = event['eventSource']
        else:
            msg['eventSource'] = 'int:invokeCLI:{}'.format(me)
        #TODO: send remaining inputs

        for x in range(count):
            payload=json.dumps(msg)
            now = time.time() * 1000
            invoke_response = lambda_client.invoke(FunctionName=fn,
                InvocationType='Event', Payload=payload) #Event type says invoke asynchronously
            nowtmp = time.time() * 1000
            delta = nowtmp-now
            me_str = 'REQ:{}:{}:{}:TIMER:INVOKE:{}'.format(reqID,me,count,delta)
    else:
        me_str = 'No_context_functionName_or_recursion:{}:{}:{}:{}'.format(reqID,me,count,fn)
    
    if invoke_response:
        reqID = 'unknown'
        if 'ResponseMetadata' in invoke_response:
            meta = invoke_response['ResponseMetadata']
            if 'HTTPHeaders' in invoke_response['ResponseMetadata']:
                headers = meta['HTTPHeaders']
                if 'x-amzn-requestid' in headers:
                    reqID = headers['x-amzn-requestid']
                if 'x-amzn-trace-id' in headers:
                    reqID += ':{}'.format(headers['x-amzn-trace-id'])
        status = 'unknown'
        if 'StatusCode' in invoke_response:
            status = invoke_response['StatusCode']
        logger.warn('{} invoke_response: reqId:{} statusCode:{}'.format(me,reqID,status))

    exit = time.time() * 1000
    ms = exit-entry
    me_str += ':TIMER:CALL:{}'.format(ms)
    logger.warn(me_str)
    return me_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='invoke Test')
    # for this table, we assume key is name of type String
    parser.add_argument('functionName',action='store',help='ARN to invoke')
    parser.add_argument('eventSource',action='store',help='value')
    parser.add_argument('--count',action='store',default=1,type=int,help='value')
    args = parser.parse_args()
    event = {'functionName':args.functionName,'eventSource':args.eventSource,'count':args.count}
    handler(event,None)
