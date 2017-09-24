import json,time,os,sys,argparse,statistics
from pprint import pprint
from graphviz import Digraph
from enum import Enum

#tuple object enumeration (positions)
TYPE='typ' #fn,sdk,sdkT (sdkTrigger)
REQ='req'
PAYLOAD='pl'
TS='ts'
DUR='dur'
CHILDREN='children'

DEBUG = False
REQS = {}
SUBREQS = {} #for functions triggered (in/)directly by other functions
TRIGGERS = {}
SDKS = []
eleID = 1
##################### getName #######################
def getName(req):
    pl = req[PAYLOAD]
    name = ''
    if pl.startswith('SDKstart:'):
        idx = pl.find(':',9)
        idx2 = pl.find('(',idx+1)
        op = pl[9:idx] 
        svc = pl[idx+1:idx2]
        name = '{} {}'.format(svc,op)
        if 'PutObject' in pl: 
            pass
        elif 'PutItem' in pl: 
            #dynamodb.us-west-2.amazonaws.com
            idx = pl.find('/dynamodb.')
            idx2 = pl.find('.amazonaws.com')
            name += ' {}'.format(pl[idx+10:idx2])
            idx = pl.find('TableName:')
            idx2 = pl.find(':',idx+10)
            name += '\n{} key=id'.format(pl[idx+10:idx2])
        elif  'Publish' in pl: 
            pass
        elif 'Invoke' in pl:
            pass
        else:
            name = 'NONTRIGGER:{}'.format(name)
            idx = pl.find('/dynamodb.')
            if (idx != -1):
                idx2 = pl.find('.amazonaws.com')
                name += '\n{}'.format(pl[idx+10:idx2])
                idx = pl.find('TableName:')
                if idx != -1:
                    idx2 = pl.find(':',idx+10)
                    name += ' {} key=id'.format(pl[idx+10:idx2])
    elif ':function:' in pl:
        idx = pl.find(':function:')
        idx2 = pl.find(':',idx+10)
        name = pl[idx+10:idx2] #add reqID if instance
        idx = pl.find('aws:lambda:') #get region
        idx2 = pl.find(':',idx+11)
        name = '{} {}'.format(pl[idx+11:idx2],name)
        
    else:
        assert True #shouldn't be here

    return name

##################### processDotChild #######################
def processDotChild(dot,req):
    global eleID
    dur = req[DUR]
    name = getName(req)
    if name.startswith('NONTRIGGER:'):
        name = name[11:]
        nodename = '{}\navg: {:0.1f}ms'.format(name,dur)
        dot.node(name,nodename,fillcolor='gray',style='filled')
    else:
        nodename='{}\navg: {:0.1f}ms'.format(name,dur)
        dot.node(name,nodename)
    eleID += 1
    for child in req[CHILDREN]:
        child_name = processDotChild(dot,child)
        dot.edge(name,child_name)
    return name

##################### processRecord #######################
def makeDotAggregate():
    global eleID
    dot = Digraph(comment='GRAggregate',format='pdf')
    agent_name = "Clients"
    dot.node(agent_name,agent_name)
    s3_name = "s3 IPbkt722 filedir test"
    s3label= "s3 IPbkt722/filedir/test\navg: ??ms"
    dot.node(agent_name,agent_name)
    dot.node(s3_name,s3label)
    dot.edge(agent_name,s3_name)

    #req = {TYPE:'fn,sdk,sdkT',REQ:reqID,PAYLOAD:pl,TS:ts,DUR:dur,CHILDREN:[]}
    for key in REQS:
        req = REQS[key]
        pl = req[PAYLOAD]
        name = getName(req)
        dur = req[DUR]
        nodename='{}\navg: {:0.1f}ms'.format(name,dur)
        dot.node(name,nodename)
        dot.edge(s3_name,name)
        url_name = "HTTP POST\nwww.cs.ucsb.edu/racelab"
        url_label = "HTTP POST\nwww.cs.ucsb.edu/racelab\navg: 162ms"
        dot.node(url_name,url_label)
        dot.edge(name,url_name)
        eleID += 1

        for child in req[CHILDREN]:
            child_name = processDotChild(dot,child)
            dot.edge(name,child_name)

    url_name = "HTTP POST\nhttpbin.org/post"
    url_label = "HTTP POST\nhttpbin.org/post\navg: 314ms"
    name = 'us-east-1 UpdateWebsiteS'
    dot.node(url_name,url_label)
    dot.edge(name,url_name)
    dot.render('gragggraph', view=True)
    return

##################### processEventSource #######################
def processEventSource(pl):
    details = ''
    idx = pl.find(':es:')
    assert idx != -1
    event_source = pl[idx:]
    if ':ddb:' in event_source:
        #keys:id:op:INSERT
        idx = event_source.find(':ddb:')
        idx2 = event_source.find(':',idx+5)
        tname = event_source[idx+5:idx2]
        idx3 = event_source.find(':',idx2+1)
        region = event_source[idx2+1:idx3]

        idx = event_source.find(':keys:')
        idx2 = event_source.find(':',idx+6)
        keyname=event_source[idx+6:idx2].replace('/','_|_')
        idx3 = event_source.find(':op:')
        key=event_source[idx2+1:idx3].replace('/','_|_')
        details = '{}:{}:{}:{}'.format(tname,region,keyname,key)
    return details

##################### processChild #######################
def processChild(child_dict):
    details = ''
    #if child is a possible event source, it can also be a parent
    #{TYPE:'fn,sdk,sdkT',REQ:reqID,PAYLOAD:pl,TS:ts,DUR:dur,CHILDREN:[]}
    payload = child_dict[PAYLOAD]
    if 'PutItem:' in payload:
        reg='unknown'
        if 'us-east-1.amazonaws.com' in payload:
            reg='us-east-1'
        elif 'us-west-2.amazonaws.com' in payload:
            reg='us-west-2'
        else:
            assert True #unhandled region
        idx = payload.find('TableName:')
        assert idx > -1
        idx2 = payload.find(':',idx+10)
        assert idx2 > -1
        tname = payload[idx+10:idx2]

        idx = payload.find(':Item:{')
        assert idx > -1
        idx2 = payload.find('}',idx+7)
        if idx2 == -1:
            idx2 = len(payload)
        item = payload[idx+7:idx2]

        item = item.split(' ')
        #rewrite name to strip off any excess characters and replace frontslash just in case it causes pbms
        keyname = item[0].strip('\'\\ ,:').replace('/','_|_')
        key = item[1].strip('\'\\ ,').replace('/','_|_')
        details = '{}:{}:{}:{}'.format(tname,reg,keyname,key)
        
    elif 'PutObject:' in payload:
        #get bucket and key
        pass
    elif 'Publish:' in payload:
        #getsubject and topic
        pass
    elif 'Invoke:' in payload:
        #get function name we are calling
        pass
    return details
    
##################### processRecord #######################
def processRecord(reqID,pl,ts):
    if pl.startswith('pl:arn:aws:lambda'):
        #entry
        SDKS.append((reqID,pl,ts))
        assert reqID not in REQS
        ele = {TYPE:'fn',REQ:reqID,PAYLOAD:pl,TS:ts,DUR:0.0,CHILDREN:[]}

        retn = processEventSource(pl)
        if retn != '': #this lambda was triggered by an event source
            assert retn in TRIGGERS
            parent = TRIGGERS[retn]
            parent[CHILDREN].append(ele)
            SUBREQS[reqID] = ele
        else: 
            REQS[reqID] = ele
        return
    if pl == 'end':
        #exit
        laststart = SDKS.pop()
        assert ':es:' in laststart[1] #that laststart is an etry
        assert reqID == laststart[0] #that laststart and this exit have same reqID

        #get the object out of REQs and update its duration
        if reqID in REQS:
            entryEle = REQS[reqID]
        else: 
            entryEle = SUBREQS[reqID]
        dur = ts-entryEle[TS]
        entryEle[DUR] = dur
        return
    if pl.startswith('SDKstart'):
        SDKS.append((reqID,pl,ts))
        return
    if pl.startswith('SDKend'):
        laststart = SDKS.pop()
        assert laststart[0] == reqID  #true of we hit an end without a start

        #update the SDKs duration
        start_pl = laststart[1]
        start_ts = laststart[2]
        dur = ts-start_ts
        #make a child object
        child = {TYPE:'sdk',REQ:reqID,PAYLOAD:start_pl,TS:start_ts,DUR:dur,CHILDREN:[]}
        #if child is a possible event source, it can also be a parent
        retn = processChild(child)
        if retn != '':
            #child is a potential trigger
            child[TYPE] = 'sdkT'
            assert retn not in TRIGGERS
            TRIGGERS[retn] = child

        #add the SDK as a child to its entry in REQS
        if reqID in REQS:
            parent = REQS[reqID]
        else: 
            parent = SUBREQS[reqID]
        parent[CHILDREN].append(child)
        return
    assert True #we shouldn't be here

##################### parseIt #######################
def parseItS(fname):
    with open(fname,'r') as f:
        for line in f:
            if DEBUG:
                print('processing: {}:{}'.format(fname,line))
            line = line.strip()
            if line == '':
                continue
            if line.find(' REMOVE:') != -1 and line.endswith(':None'):
                continue
            if line.find(' INSERT:') == -1:
                print('Error: unexpected entry: {}'.format(line))
                sys.exit(1)
            pl = reqID = ts = None
            if '"SDKstart:' in line or "'SDKstart:" in line:
                startidx = line.find('SDKstart')
                idx = line.find("}, 'reqID': {'S': '")
                tsidx = line.find("ts': {'N': '")
                pl_str = line[startidx:idx]
                reqID_str = line[idx+19:tsidx]
                ts_str = line[tsidx+12:]
            else: 
                toks = line.split(' ')
                pl_str = toks[3]
                reqID_str = toks[6]
                ts_str = toks[9]
            pl = pl_str.strip("'\",}{ ")
            ts = float(ts_str.strip("'\",}{ "))
            reqID = reqID_str.strip("'\",}{ ")
            idx = reqID.find(':')
            reqID = reqID[:idx]
            if DEBUG:
                print('\n{}\n{}\n{}'.format(pl,reqID,ts))
            processRecord(reqID,pl,ts)

 
##################### main #######################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Stream Dump Parser')
    parser.add_argument('fname',action='store',help='filename containing data')
    parser.add_argument('--dbdump',action='store_true',default=False,help='file is in json dynamodump format')
    parser.add_argument('--dynamic',action='store_true',default=False,help='file is in json streamD format')
    parser.add_argument('--static',action='store_true',default=False,help='file is in json streamS format')
    args = parser.parse_args()

    if not args.dbdump and not args.dynamic and not args.static:
        parser.print_help()
        print('\nError: must choose one of the three file types')
        sys.exit(1)

    if args.dbdump or args.dynamic:
        parser.print_help()
        print('\nError: dbdump and dynamic not supported yet')
        sys.exit(1)

    if args.static:
        parseItS(args.fname)
        assert SDKS == []
        makeDotAggregate()
        

###### streamD #############
#2600000000030190189341 REMOVE:09b32782c5ba1c16486697264e2e3af6:None
#2100000000030189636257 INSERT:43aa94cb211c9a9d7df7ae4aca726b7b:{'payload': {'S': 'pl:9d656195-9f26-11e7-a691-417687e452d3:arn:aws:lambda:us-west-2:443592014519:function:ImageProcPyB:es:ext:invokeCLI'}, 'reqID': {'S': '9d656195-9f26-11e7-a691-417687e452d3:entryb620498e'}, 'ts': {'N': '1506037385780'}}
#2200000000030189638411 INSERT:89df83c823bf38b3f38cee963eb1b6fd:{'payload': {'S': '{"type": "subsegment", "id": "ae34be6cb75e4526", "trace_id": "1-59c44e89-9b998015677b4d7fbe3a313d", "parent_id": "564686485923084a", "start_time": 1506037387.3388684, "end_time": 1506037387.5118344, "name": "DynamoDB", "namespace": "aws", "aws": {"operation": "PutItem", "region": "us-west-2", "table_name": "image-proc-B", "gr_payload": "payload:arn:aws:lambda:us-west-2:443592014519:function:ImageProcPyB:TableName:image-proc-B:Item:{\'id\': \'imgProc/d1.jpg2e46\', \'labels\': \'[{\\"Name\\": \\"Animal\\", \\"Confidence\\": 96.52118682861328}, {\\"Name\\": \\"Gazelle\\", \\"Confidence\\": 96.52118682861328}, {\\"Name\\": \\"Impala\\", \\"Confidence\\": 96.52118682861328}, {\\"Name\\": \\"Mammal\\", \\"Confidence\\": 96.52118682861328}, {\\"Name\\": \\"Wildlife\\", \\"Confidence\\": 96.52118682861328}, {\\"Name\\": \\"Deer\\", \\"Confidence\\": 91.72703552246094}]\'}", "request_id": "5EILHOMITKB4EJ4QI3DNHSMLB7VV4KQNSO5AEMVJF66Q9ASUAAJG"}, "http": {"response": {"status": 200}}, "error": false}'}, 'reqID': {'S': '9d656195-9f26-11e7-a691-417687e452d3:a743431b'}, 'ts': {'N': '1506037387512'}}

###### streamS #############
#7699400000000028634767231 INSERT:4f1897c7952cc7d63434cec73ff25c66:{'payload': {'S': 'pl:arn:aws:lambda:us-west-2:443592014519:function:ImageProcPyS:es:ext:invokeCLI'}, 'reqID': {'S': 'beb132a4-a06e-11e7-8dc2-e36d371b8422:entryd33a0531'}, 'ts': {'N': '1506178326328'}}
#7699500000000028634769201 INSERT:9056a6b087408f686de60fb21280329c:{'payload': {'S': "SDKstart:DetectLabels:rekognition(https://rekognition.us-west-2.amazonaws.com)::Image:{'S3Object': {'Bucket': 'cjktestbkt', 'Name': 'imgProc/d1.jpg'}}:MaxLabels:10:MinConfidence:90"}, 'reqID': {'S': 'beb132a4-a06e-11e7-8dc2-e36d371b8422:bebf27f1'}, 'ts': {'N': '1506178330288'}}
#7699600000000028634769773 INSERT:48763c117834d8a082f16178963c0f21:{'payload': {'S': 'SDKend:1261.327392578125'}, 'reqID': {'S': 'beb132a4-a06e-11e7-8dc2-e36d371b8422:fe3f8ed2'}, 'ts': {'N': '1506178331549'}}
#7700700000000028634784713 INSERT:fe571e980a5131181e1a469e485ae5c7:{'payload': {'S': 'end'}, 'reqID': {'S': 'eef61fb6-b1b0-48f7-b721-b5367c7aa7e0:entry8494cb13:exit8494cb13'}, 'ts': {'N': '1506178356246'}}
#7700800000000028635010684 REMOVE:7f04785cbdc183ace7c1b74e0d58a948:None

#cjk/streamS.base:7699500000000028634769201 INSERT:9056a6b087408f686de60fb21280329c:{'payload': {'S': "SDKstart:DetectLabels:rekognition(https://rekognition.us-west-2.amazonaws.com)::Image:{'S3Object': {'Bucket': 'cjktestbkt', 'Name': 'imgProc/d1.jpg'}}:MaxLabels:10:MinConfidence:90"}, 'reqID': {'S': 'beb132a4-a06e-11e7-8dc2-e36d371b8422:bebf27f1'}, 'ts': {'N': '1506178330288'}}
