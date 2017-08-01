import boto3
import json, logging, time, argparse

def handler(event, context):
    entry = time.time() * 1000
    logger = logging.getLogger()
    retn = 'nothing:returned'
    eventSource = 'unknown'
    if context:
        logger.info('SpotTemplatePy::handler: context: {}'.format(context))
    if event:
        logger.info('SpotTemplatePy::handler: event: {}'.format(event))
        if 'eventSource' in event:
            eventSource = event['eventSource']
        elif 'EventSource' in event:
            eventSource = event['EventSource']
        
        if 'requestContext' in event:
            #API Gateway
            logger.warn('SpotTemplatePy::handler: API Gateway triggered')
        elif 'Records' in event:
            #S3 or DynamoDB or SNS or unknown
            recs = event['Records']
            obj = recs[0]
            if 'eventSource' in obj:
                eventSource = obj['eventSource']
            if 'EventSource' in obj: #aws:sns
                eventSource = obj['EventSource']
            if eventSource.startswith('aws:s3'):
                logger.warn('SpotTemplatePy::handler: S3 triggered')
            elif eventSource.startswith('aws:dynamodb'):
                logger.warn('SpotTemplatePy::handler: dynamoDB triggered')
            elif eventSource.startswith('aws:sns'):
                logger.warn('SpotTemplatePy::handler: SNS triggered')
            else:
                logger.warn('SpotTemplatePy::handler: unknown Records trigger: {}'.format(eventSource))
        elif 'invokeCLI' in eventSource:
            logger.warn('SpotTemplatePy::handler: invoke trigger: {}'.format(eventSource))
        else:
            logger.warn('SpotTemplatePy::handler: unknown trigger: {}'.format(eventSource))

    inv = time.time() * 1000
    retn = invokeCLI(event,context,logger) #invoke the function passed in 
    invend = time.time() * 1000
    ms = invend-entry
    invms = inv-entry
    retn += ':SpotTemplatePy:ts:{}:setup:{}:invoke:{}'.format(invend,ms,invms)
    me_str = 'TIMER:CALL:{}:INVOKE:{}'.format(ms,invms)
    logger.warn(me_str)
    return retn

def invokeCLI(event,context,logger):
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
    if event:
        if 'functionName' in event:
            fn = event['functionName']

    #run_lambda does not support invoke via Payload arg
    invoke_response = None
    if fn and fn != me:
        now = time.time() * 1000
        msg = {}
        msg['msg'] = 'from {} at {}'.format(me,now)
        msg['requestId'] = reqID
        if event and 'eventSource' in event and me == 'unknown': 
            msg['eventSource'] = event['eventSource']
        else:
            msg['eventSource'] = 'int:invokeCLI:{}'.format(me)

	#do not set functionName here as you risk getting into an infinite loop!
        payload=json.dumps(msg)
        logger.warn('SpotTemplatePy::handler sending payload to {}: {}'.format(fn,msg))

        invoke_response = lambda_client.invoke(FunctionName=fn,
            InvocationType='Event', Payload=payload) #Event type says invoke asynchronously
        nowtmp = time.time() * 1000
        delta = nowtmp-now
        ms = int(round(delta))
        me_str = 'REQ:{}:TIMER:CALL:{}:{}'.format(reqID,me,ms)
    else:
        me_str = 'No context, no functionName, or call will cause recursion: {}:fn:{}'.format(me,fn)
    
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

    logger.warn('SpotTemplatePy::handler returning: {}'.format(me_str))
    return me_str

if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description='invoke Test')
    # for this table, we assume key is name of type String
    parser.add_argument('functionName',action='store',help='ARN to invoke')
    parser.add_argument('eventSource',action='store',help='value')
    args = parser.parse_args()
    event = {'functionName':args.functionName,'eventSource':args.eventSource}
    invokeCLI(event,None,logger)
