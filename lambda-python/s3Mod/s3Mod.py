import boto3
import json, logging, argparse, time

def handler(event, context):
    entry = time.time() * 1000
    logger = logging.getLogger()
    if not context: #calling from main so set the profile we want
        session = boto3.Session(profile_name='cjk1')
        s3_client = session.resource('s3')
    else:
        s3_client = boto3.resource('s3')
        logger.info('s3Mod::handler: context: {}'.format(context))

    fname = None
    cont = None
    prefix = None
    bkt = None
    if event:
        logger.info('s3Mod::handler: event: {}'.format(event))
        if 'file_content' in event:
            cont = event['file_content']
        if 'prefix' in event:
            prefix = event['prefix']
        if 'bkt' in event:
            bkt = event['bkt']
        if 'fname' in event:
            fname = event['fname']


    if fname and cont and prefix and bkt:
        logger.info('s3Mod.handler: writing to s3 bucket {}: {}/{}'.format(bkt,prefix,fname))
        s3obj = s3_client.Object('{}'.format(bkt), '{}/{}'.format(prefix,fname))
 	#write 
        s3obj.put(Body=cont)
 	#read 
        strOutput = s3obj.get()['Body'].read().decode('utf-8')
        #for n in strOutput: #for debugging only, prints a char at a time
            #print('cjk: {}'.format(n))
    else:
        logger.warn('s3Mod.handler: insufficient arguments passed in (prefix,file_content,bkt, and fname required)')

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
    parser.add_argument('file_content',action='store',help='file_content')
    args = parser.parse_args()
    event = {'bkt':args.bkt,'prefix':args.prefix,'fname':args.fname,'file_content':args.file_content}
    handler(event,None)
