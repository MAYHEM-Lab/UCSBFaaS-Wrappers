import json,time,os,sys,argparse
import ast,statistics
from pprint import pprint

DEBUG = False
def processJson(fname,getReq=None,fns=[]):
    if DEBUG:
        fn = fname
        idx = fname.rfind('/')
        if idx > -1:
            fn = fname[idx+1:]
        #print('processing file: {} and reqID {}'.format(fn,reqID))
        print('processing file: {}'.format(fn))
    with open(fname) as data_file:    
        data = json.load(data_file)

    count = data['Count']
    items = data['Items']
    print('count {}'.format(count))
    for item in items:
        try:
            req = item['reqID']['S']
        except KeyError as e:
            print('Are you sure you are passing in the right dump file? (spotFns or gammaRays)')
            print(e)
            sys.exit(1)
           
        if getReq and not req.startswith(getReq):
            continue
        ts = float(item['ts']['N'])
        payload = item['payload']['S']
        if payload.startswith('pl:'): #pl:reqID:arn functionEntry
            print('ENTRY:{} {}'.format(req,payload))
        else:
            try:
                pl = json.loads(payload)
            except json.decoder.JSONDecodeError as e:
                print('{} {}'.format(req,payload))
                continue
            start = float(pl['start_time'])
            aws = pl['aws']
            op = aws['operation']
            print('{} {}'.format(start,json.dumps(aws)))
            #print('{}\n\t{}::{}'.format(req,payload,ts))
            #if 'gr_payload' in aws:
                #print('\t{}'.format(aws['gr_payload']))

if __name__ == "__main__":
    global INCLUDE_READS
    parser = argparse.ArgumentParser(description='DynamoDB spotFns Table data Parser')
    parser.add_argument('fname',action='store',help='filename to process')
    parser.add_argument('--reqID',action='store',default=None,help='reqID to filter')
    parser.add_argument('--fns',action='store',default='',help='colon delimited list to filter on')
    args = parser.parse_args()
    fname = args.fname
    if not os.path.exists(fname):
        print('Unable to find/open file')
        sys.exit(1)
    fns = args.fns.split(':')

    reqID = args.reqID
    if os.path.isfile(fname) and fname.endswith('.json') and not fname.startswith('.'):
        processJson(fname,reqID)
    else: #a directory
        path = os.path.abspath(fname)
        for f in os.listdir(path):
            findir = os.path.join(path, f)
            if os.path.isfile(findir) and findir.endswith('.json') and not f.startswith('.'):
                processJson(findir,reqID,fns)

