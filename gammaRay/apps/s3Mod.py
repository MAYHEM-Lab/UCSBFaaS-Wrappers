import boto3
import json, logging, argparse, time, uuid

def handler(event, context):
    entry = time.time() * 1000
    logger = logging.getLogger()
    if not context: #calling from main so set the profile we want
        session = boto3.Session(profile_name='cjk1')
        s3_client = session.resource('s3')
    else:
        s3_client = boto3.resource('s3')

    fname = None
    cont = None
    prefix = None
    bkt = None
    if event:
        if 'file_content' in event:
            cont = event['file_content']
        if 'prefix' in event:
            prefix = event['prefix']
        if 'bkt' in event:
            bkt = event['bkt']
        if 'fname' in event:
            fname = event['fname']
        if 'Records' in event:
            #triggered 
            rec = event['Records'][0]
            es = 'unknown'
            if 'EventSource' in rec:
                es = rec['EventSource']
            elif 'eventSource' in rec:
                es = rec['eventSource']
            logger.warn('s3Mod::handler: triggered by {} event: {}'.format(es,event))
            if 'Sns' in rec:
                #sns triggered
                snsObj = rec['Sns']
                mid = 'unknown'
                sub = 'unknown'
                if 'MessageId' in snsObj:
                    mid = snsObj['MessageId']
                if 'Subject' in snsObj:
                    sub = snsObj['Subject']
                if 'Message' in snsObj:
                    msg = snsObj['Message']
                    fname_idx = msg.find('fname:')
                    fname_end_idx = msg.find(':',fname_idx+6)
                    if fname_idx != -1 and fname_end_idx != -1:
                        fname = msg[fname_idx+6:fname_end_idx]
                    bkt_idx = msg.find('bkt:')
                    bkt_end_idx = msg.find(':',bkt_idx+4)
                    if bkt_idx != -1 and bkt_end_idx != -1:
                        bkt = msg[bkt_idx+4:bkt_end_idx]
                    pref_idx = msg.find('prefix:')
                    pref_end_idx = msg.find(':',pref_idx+7)
                    if pref_idx != -1 and pref_end_idx != -1:
                        prefix = msg[pref_idx+7:pref_end_idx]
                    cont = str(uuid.uuid4())[:8]

    if fname and cont and prefix and bkt:
        logger.warn('s3Mod.handler: writing to s3 bucket {}: {}/{}'.format(bkt,prefix,fname))
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
    #event = {'bkt':args.bkt,'prefix':args.prefix,'fname':args.fname,'file_content':args.file_content}
    event = {'Message':'foodoofname:cjk1.txt:goprefix:testcjk:oo:bkt:cjklambdatrigger:poo'}
    handler(event,None)
