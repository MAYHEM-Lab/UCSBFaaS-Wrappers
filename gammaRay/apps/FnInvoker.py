import boto3
import os, json, logging, time, argparse, requests, uuid

def handler(event,context):
    entry = time.time() * 1000
    logger = logging.getLogger()
    me = 'unknown'
    reqID = 'unknown'
    if not context: #invoking from main
        boto3.setup_default_session(profile_name='cjk1')
        me = 'arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyC'
    else:
        me = context.invoked_function_arn
        reqID = context.aws_request_id
        slist = ''
        for k in os.environ:
            slist += '{}:{};'.format(k,os.environ[k])
      
    #time.sleep(330) for testing error reporting in AWS Lambda
    reg = 'us-west-2'
    if event:
        if 'region' in event:
            reg = event['region']
    lambda_client = boto3.client('lambda',region_name=reg)

    fn = None
    count = 1
    if event:
        if 'functionName' in event:
            fn = event['functionName']
        if 'count' in event:
            count = int(event['count'])
        a = b = 0
        if 'a' in event:
            a = int(event['a'])
        if 'b' in event:
            b = int(event['b'])
        if 'op' in event:
            op = event['op']
            res = 0
            if op == '+':
                res = a+b
            if op == '-':
                res = a-b
            if op == '*':
                res = a*b
            if op == '/':
                res = a/b
            print(res)
        if 'Records' in event:  #for webApp --> invoke DBModPy_ if invoked via S3
            #triggered 
            rec = event['Records'][0]
            es = 'unknown'
            if 'EventSource' in rec:
                es = rec['EventSource']
            elif 'eventSource' in rec:
                es = rec['eventSource']
            logger.warn('FnInvokerPy::handler: triggered by {} event: {}'.format(es,event))
            idx = me.find(':FnInvokerPy')
            assert idx != -1
            tail = me[idx+12:]
            arn = me[0:idx]
            if 'aws:s3' in es:
                fn = '{}:DBModPy{}'.format(arn,tail)
                msg = {"from":"{}".format(me)}
                payload=json.dumps(msg)
                print('Invoking {}'.format(fn))
                invoke_response = lambda_client.invoke(FunctionName=fn,
                    InvocationType='Event', Payload=payload) #Event type says invoke asynchronously
                return invoke_response

        #test the above via calling from main (add 'test' to event)
        if 'test' in event:  #for webApp --> invoke DBModPy_ if invoked via S3
            #triggered 
            es = 'unknown'
            if 'EventSource' in event:
                es = event['EventSource']
            elif 'eventSource' in event:
                es = event['eventSource']
            logger.warn('FnInvokerPy::handler: triggered by {} event: {}'.format(es,event))
            idx = me.find(':FnInvokerPy')
            assert idx != -1
            tail = me[idx+12:]
            arn = me[0:idx]
            if 'aws:s3' in es:
                fn = '{}:DBModPy{}'.format(arn,tail)
                msg = {"from":"{}".format(me)}
                payload=json.dumps(msg)
                print('Invoking {}'.format(fn))
                invoke_response = lambda_client.invoke(FunctionName=fn,
                    InvocationType='Event', Payload=payload) #Event type says invoke asynchronously
                return invoke_response
            

    #run_lambda does not support invoke via Payload arg
    invoke_response = None
    key = val = None
    if fn and fn != me:
        msg = {}
        now = time.time() * 1000
        msg['msg'] = 'from:{}:at:{}'.format(me,now)
        msg['requestId'] = reqID
        if event and 'eventSource' in event and me == 'unknown': 
            msg['eventSource'] = event['eventSource']
        else:
            msg['eventSource'] = 'int:invokeCLI:{}'.format(me)
        #TODO: send remaining inputs
        #sending only the ones used in the other apps
        if 'tablename' in event: 
            msg['tablename'] = event['tablename']
        if 'mykey' in event: 
            key = msg['mykey'] = event['mykey']
        if 'myval' in event: 
            val = msg['myval'] = event['myval']
        if 'bkt' in event: 
            msg['bkt'] = event['bkt']
        if 'prefix' in event: 
            msg['prefix'] = event['prefix']
        if 'fname' in event: 
            msg['fname'] = event['fname']
        if 'file_content' in event: 
            msg['file_content'] = event['file_content']
        if 'topic' in event: 
            msg['topic'] = event['topic']
        if 'subject' in event: 
            msg['subject'] = event['subject']
        if 'msg' in event: 
            msg['msg'] += ":{}".format(event['msg'])

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

    #post to website
    if not key or not val:
        key = str(uuid.uuid4())[:4]
        val = 17
    r = requests.post('http://httpbin.org/post', data = {key:val})
    print('HTTP POST status: {}'.format(r.status_code))

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
    parser.add_argument('--region',action='store',default='us-west-2',help='aws region')
    args = parser.parse_args()
    event = {'functionName':args.functionName,'eventSource':args.eventSource,'count':args.count,'region':args.region,'test':'yes'}
    handler(event,None)
