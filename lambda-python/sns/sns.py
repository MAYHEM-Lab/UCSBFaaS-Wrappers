import boto3
import json, logging, argparse, os, time

def handler(event, context):
    entry = time.time() * 1000
    logger = logging.getLogger()
    if context:
        logger.info('sns::handler: context: {}'.format(context))
        if event:
            logger.info('sns::handler: event: {}'.format(event))
    else: #calling from main (testing)
        boto3.setup_default_session(profile_name='cjk1')
    sns = boto3.client('sns')
    arn = None
    subj = 'test'
    msg = 'hello world'
    if event:
        if 'topic' in event:
            arn = event['topic']
        if 'subject' in event:
            subj = event['subject']
        if 'msg' in event:
            msg = event['msg']

    if arn:
        sns.publish(
            TopicArn=arn,
            Subject=subj,
            Message=msg
        )

    exit = time.time() * 1000
    ms = exit-entry
    me_str = 'TIMER:CALL:0:HANDLER:ts:{}:duration:{}'.format(exit,ms)
    logger.warn(me_str)
    return me_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='post to sns')
    #create an SNS topic first, then name of which you pass in
    parser.add_argument('topic',action='store',help='aws sns testtopic arn')
    parser.add_argument('subject',action='store',help='key')
    parser.add_argument('msg',action='store',help='value')
    args = parser.parse_args()
    event = {'topic':args.topic,'subject':args.subject,'msg':args.msg}
    handler(event,None)
