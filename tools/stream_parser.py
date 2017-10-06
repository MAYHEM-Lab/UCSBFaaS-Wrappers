import json,time,os,sys,argparse,statistics,ast
from pprint import pprint
from graphviz import Digraph
from enum import Enum
from collections import defaultdict

#tuple object enumeration (positions)
TYPE='typ' #fn,sdk,sdkT (sdkTrigger)
REQ='req'
PAYLOAD='pl'
TS='ts'
SEQ='seqNo'
DUR='dur'
CHILDREN='children'

DEBUG = True
REQS = {}
SUBREQS = {} #for functions triggered (in/)directly by other functions
TRIGGERS = defaultdict(list)
SDKS = []
REPEATS = []
eleID = 1
seqID = 1
NODES = {}
##################### getName #######################
def getName(req):
    #to match: details = '{}:{}:{}:{}'.format(tname,region,keyname,key)
    pl = req[PAYLOAD]
    name = '{}:{}:{}:{}'.format(pl['tname'],pl['reg'],pl['kn'],pl['key'])
    rest = '{} {}'.format(pl['op'],pl['rest'])
    return rest,name

##################### processDotChild #######################
def processDotChild(dot,req):
    global eleID
    dur = req[DUR]
    rest,name = getName(req)
    if name.startswith('NONTRIGGER:'):
        name = name[11:]
        totsum = dur
        count = 1
        if name in NODES:
            (t,c) = NODES[name]
            totsum+=t
            count += c
        NODES[name] = (totsum,count)
        avg = totsum/count 
        nodename = '{}\navg: {:0.1f}ms'.format(name,avg)
        dot.node(name,nodename,fillcolor='gray',style='filled')
    else:
        totsum = dur
        count = 1
        if name in NODES:
            (t,c) = NODES[name]
            totsum+=t
            count += c
        NODES[name] = (totsum,count)
        avg = totsum/count 
        nodename='{}\navg: {:0.1f}ms'.format(name,avg)
        dot.node(name,nodename)
    eleID += 1
    for child in req[CHILDREN]:
        child_name = processDotChild(dot,child)
        dot.edge(name,child_name)
    return name

##################### makeDotAggregate #######################
def makeDotAggregate():
    global eleID
    dot = Digraph(comment='GRAggregate',format='pdf')
    agent_name = "Clients"
    dot.node(agent_name,agent_name)
    agent_edges = []

    #req = {TYPE:'fn,sdk,sdkT',REQ:reqID,PAYLOAD:pl,TS:ts,DUR:dur,CHILDREN:[]}
    for key in REQS:
        req = REQS[key]
        pl = req[PAYLOAD]
        rest,name = getName(req)
        dur = req[DUR]
        totsum = dur
        count = 1
        if name in NODES:
            (t,c) = NODES[name]
            totsum+=t
            count += c
        NODES[name] = (totsum,count)
        avg = totsum/count 
        nodename='{}\navg: {:0.1f}ms'.format(name,avg)
        dot.node(name,nodename)
        if name not in agent_edges: 
            dot.edge(agent_name,name)
            agent_edges.append(name)
        eleID += 1

        for child in req[CHILDREN]:
            child_name = processDotChild(dot,child)
            dot.edge(name,child_name)

    dot.render('gragggraph', view=True)
    return

##################### processEventSource #######################
def processEventSource(pl):
    ''' returns True/False, payload '''
    retn = {}
    event_source = pl
    triggered = False
    if ':es:lib:invokeCLI:' in event_source: #Invoke trigger
        triggered = True
        #pl:arn:aws:lambda:us-west-2:443592014519:function:emptyB:es:lib:invokeCLI:FnInvokerPyB:ed086648-aa47-11e7-a1cd-4dab0b1999f4
        toks = pl.split(':')
        retn['reg'] = toks[4] #region of both caller and callee
        retn['name'] = toks[7] #this fn's (callee) name
        retn['tname'] = toks[11] #caller's name
        retn['kn'] = toks[12] #caller reqID
        retn['op'] = 'Invoke' #triggering operation
        #key 'key' not used

    elif ':ddb:' in event_source: #DDB update trigger
        triggered = True
        #pl:arn:aws:lambda:us-east-1:443592014519:function:UpdateWebsiteB:esARN:arn:aws:dynamodb:us-west-2:443592014519:table/image-proc-S/stream/2017-09-20T20:26:50.795:keys:id:op:INSERT
        #us-west-2:443592014519:function:DBSyncPyB:esARN:arn:aws:dynamodb:us-west-2:443592014519:table/image-proc-B/stream/2017-10-05T21:42:44.663:es:ddb:keys:id:{"S": "imgProc/d1.jpg1428"}:op:INSERT
        toks = pl.split(':')
        retn['reg'] = toks[4] #region of both caller and callee
        retn['name'] = toks[7] #region of both caller and callee
	#get tablename
        assert pl.find('esARN:') != -1
        tmp_tname = toks[14].split('/')
        print(tmp_tname,pl)
        retn['tname'] = tmp_tname[1]
        retn['kn'] = toks[16]
        retn['op'] = toks[18]
        retn['rest'] = '{} {}'.format(toks[12],toks[14]) #table region, stream ID
    else:
        print(pl)
        assert True
    return triggered,retn

##################### processPayload #######################
def processPayload(pl,reqID):
    #pl:PutItem:us-west-2:TableName:image-proc-B:Item:{"id": "imgProc/d1.jpg0b92", "labels": "[{"Name": "Animal", "Confidence": 96.52117156982422}, {"Name": "Gazelle", "Confidence": 96.52117156982422}, {"Name": "Impala", "Confidence": 96.52117156982422}, {"Name": "Mammal", "Confidence": 96.52117156982422}, {"Name": "Wildlife", "Confidence": 96.52117156982422}, {"Name": "Deer", "Confidence": 91.72703552246094}]"}
    #GAMMATABLE = [ 'PutItem', 'UpdateItem', 'DeleteItem', 'BatchWriteItem', 'PutObject', 'DeleteObject', 'PostObject', 'Publish', 'Invoke' ]
    #pl_str = pl_str.replace(' "[{"',' [{"')
    #pl_str = pl_str.replace(']"}"',']}"}"')
    pl = pl.strip('"}')
    if DEBUG: 
        print('ppayload: {}'.format(pl))

    retn = {'rest':'empty', 'key':'none'}
    if pl.startswith('PutItem:'):
        retn['op'] = 'DDB=PutItem'
        rest = pl[8:]
        idx = rest.find(':')
        assert idx != -1
        retn['reg'] = rest[:idx]
        idx2 = rest.find(':TableName:')
        assert idx2 != -1
        idx = rest.find(':Item:')
        assert idx != -1
        retn['tname'] = rest[idx2+11:idx]
        data = rest[idx+7:] #7 to get past the {
        toks = data.split(': ')
        retn['kn'] = toks[0].strip('"')
        toks = toks[1].split(' ')
        retn['key'] = toks[0].strip('",')
    elif pl.startswith('UpdateItem:'):
        retn['op'] = 'DDB=UpdateItem'
        rest = pl[11:]
        idx = rest.find(':')
        retn['reg'] = rest[:idx]
        print(rest)
        sys.exit(1)
    elif pl.startswith('DeleteItem:'):
        retn['op'] = 'DDB=DeleteItem'
        rest = pl[11:]
        retn['reg'] = rest[:idx]
        print(rest)
    elif pl.startswith('BatchWriteItem:'):
        retn['op'] = 'DDB=BatchWriteItem'
        rest = pl[15:]
        retn['reg'] = rest[:idx]
        print(rest)
        sys.exit(1)
    elif pl.startswith('PutObject:'):
        retn['op'] = 'S3=PutObject'
        rest = pl[10:]
        retn['reg'] = rest[:idx]
        print(rest)
        sys.exit(1)
    elif pl.startswith('DeleteObject:'):
        retn['op'] = 'S3=DeleteObject'
        rest = pl[13:]
        retn['reg'] = rest[:idx]
        print(rest)
        sys.exit(1)
    elif pl.startswith('PostObject:'):
        retn['op'] = 'S3=PostObject'
        rest = pl[11:]
        retn['reg'] = rest[:idx]
        print(rest)
        sys.exit(1)
    elif pl.startswith('Publish:'):
        retn['op'] = 'SNS=Publish'
        rest = pl[8:]
        retn['reg'] = rest[:idx]
        print(rest)
        sys.exit(1)
    elif pl.startswith('Invoke:'):
        #Invoke:us-west-2:FunctionName:arn:aws:lambda:us-west-2:443592014519:function:emptyB:InvocationType:Event
        retn['op'] = 'Invoke'
        toks = pl.split(':')
        retn['reg'] = toks[1] #region of both
        if reqID in REQS:
            me = REQS[reqID]
        else: 
            me = SUBREQS[reqID]
        print(me)
        retn['name'] = toks[9] #callee name
        retn['tname'] = me['pl']['name']  #caller name
        retn['kn'] = reqID  #caller reqID
        retn['rest'] = '{} {}'.format(toks[10],toks[11]) #invocationType, event/requestresponse
        assert toks[1] == toks[6] #make sure they are in the same region
        #key 'key' not used

    elif pl.startswith('HTTP:'):
        #pl:HTTP:us-west-2:POST:http://httpbin.org/post
        retn['op'] = 'HTTP'
        rest = pl[5:]
        idx = rest.find(':')
        assert idx != -1
        retn['reg'] = rest[:idx]
        idx2 = rest.find(':',idx+1)
        assert idx2 != -1
        retn['kn'] = rest[idx+1:idx2] #method
        idx = rest.find('http://',idx2+1)
        retn['tname'] = rest[idx+7:]
    else:
        assert True

    return retn
    
##################### processHybrid  #######################
def processHybrid(fname):
    flist = []
    #get the json from the files
    if os.path.isfile(fname):
        flist.append(fname)
    else:
        path = os.path.abspath(fname)
        for file in os.listdir(fname):
            fn = os.path.join(path, file)
            if os.path.isfile(fn) and fn.endswith('.xray'):
                flist.append(fn)

    for fname in flist:
        if DEBUG:
            print('processing xray file {}'.format(fname))
        with open(fname,'r') as f:
            json_dict = json.load(f)

        traces = json_dict['Traces']
        for trace in traces:
            segs = trace['Segments']
            for seg in segs:
                doc_dict = json.loads(seg['Document'])
                name = doc_dict['name']
                myid = seg['Id']
                if 'trace_id' in doc_dict:
                    trid = doc_dict['trace_id']
                #print(myid,doc_dict)
                start = doc_dict['start_time']
                end = doc_dict['end_time']
                if 'aws' in doc_dict:
                    aws = doc_dict['aws']
                    tname = op = reg = pl = 'unknown'
                    if 'operation' in aws:
                        op = aws['operation']
                    origin = doc_dict['origin']
                    #if origin == 'AWS::DynamoDB::Table':  #just a repeat of what we get in the subsegments
                    if origin == 'AWS::Lambda' and 'resource_arn' in doc_dict:
                        print('{} LAMBDA:{}:{}:{}:{}'.format(myid,doc_dict['resource_arn'],aws['request_id'],start,end))
                        print('\ttrid: {}'.format(trid))
                    else:
                        if 'function_arn' in aws:
                            print('{} FN:{}:{}:{}'.format(myid,aws['function_arn'],start,end))
                            print('\ttrid: {}'.format(trid))
                        else:
                            pass #can skip this as data is repeated
                            #if name != 'DynamoDB': #data is repeated here
                                #print('{} other_{}:{}:{}:{}'.format(myid,name,origin,start,end))
                                #print(doc_dict)
    
                    if 'subsegments' in doc_dict:
                        for subs in doc_dict['subsegments']:
                            subid = subs['id']
                            name = subs['name']
                            if 'aws' in subs:
                                #print('\t{}:{}:{}:{}:{}'.format(subs['name'],subs['aws']['operation'],subs['aws']['region'],subs['start_time'],subs['end_time']))
                                aws = subs['aws']
                                trid=myid=tname=op=reg='unknown'
                                if 'function_arn' in aws:
                                    fn = aws['function_arn']
                                if 'trace_id' in aws:
                                    trid = aws['trace_id']
                                if 'operation' in aws:
                                    op = aws['operation']
                                if 'table_name' in aws:
                                    tname = aws['table_name']
                                if 'region' in aws:
                                    reg = aws['region']
                                key=keyname='unknown'
                                if 'gr_payload' in aws:
                                    pl = aws['gr_payload']
                                    idx = pl.find(':Item:{')
                                    idx3 = pl.find(':FunctionName:')
                                    if idx != -1:
                                        idx2 = pl.find(':',idx+7)
                                        keyname = pl[idx+7:idx2].strip('"\' ') #DDB keyname
                                        idx = pl.find(',',idx2+1)
                                        key = pl[idx2+1:idx].strip('"\' ') #DDB key
                                    elif idx3 != -1:
                                        #payload:arn:aws:lambda:us-west-2:443592014519:function:FnInvokerPyB:FunctionName:arn:aws:lambda:us-west-2:443592014519:function:DBModPyB:InvocationType:Event:Payload
                                        idx = pl.find(':',idx3+29)
                                        reg = pl[idx3+29:idx]
                                        idx = pl.find(':function:',idx3+29)
                                        idx2 = pl.find(':',idx+10)
                                        tname = pl[idx+10:idx2] #function name
                                        idx = pl.find(':InvocationType:')
                                        idx2 = pl.find(':',idx+16)
                                        keyname= pl[idx+16:idx2] #Event (Async) or RequestResponse (Sync)
                                        key = aws['request_id'] #request ID of invoke call
                                    elif ':TopicArn:arn:aws:sns:' in pl:
                                        idx = pl.find(':TopicArn:arn:aws:sns:')
                                        pl_str = pl[idx+22:].split(':')
                                        reg = pl_str[0]
                                        tname = pl_str[2]#topicARN
                                        keyname = pl_str[4] #Subject
                                        idx = pl.find(':Message:') 
                                        key = pl[idx+9:idx+39] #first 30 chars after Message:
                                    elif ':Bucket:' in pl:
                                        idx = pl.find(':Bucket:')
                                        pl_str = pl[idx+8:].split(':')
                                        tname = pl_str[0] #bucket name
                                        keyname = pl_str[2] #keyname
                                    else:
                                        print('Unhandled GammaRay payload: {}'.format(doc_dict))
                                        assert True
                                if name == 'Initialization':
                                    assert tname == 'unknown' and 'function_arn' in aws
                                    idx = fn.find(':',15)
                                    reg = fn[15:idx] #function's region
                                    idx = fn.find(':function:')
                                    tname = fn[idx+10:] #function name
                                print('\t{} {}:{}:{}:{}:{}:{}:{}:{}'.format(subid,name,op,reg,tname,keyname,key,subs['start_time'],subs['end_time']))
    
                            else:
                                if name == 'requests':
                                    assert 'http' in subs
                                    http = subs['http']
                                    url = http['request']['url'][7:] #trim off the http:// chars
                                    op = http['request']['method']
                                    status = http['response']['status']
                                    print('\t{} {}:{}:{}:{}:{}:{}'.format(subid,name,op,url,status,subs['start_time'],subs['end_time']))
                                else:
                                    print('\t{} UNKNOWN:{}:{}:{}'.format(subid,name,subs['start_time'],subs['end_time']))
                else:
                    pass #can skip this as they are repeats
                    #print(doc_dict)
                    
    print('DONE')
            
   

##################### parseIt #######################
def parseIt(fname,fxray=None):
    global seqID
    if DEBUG:
        print('processing stream {}'.format(fname))
    with open(fname,'r') as f:
        for line in f:
            line = line.strip()
            if line == '':
                continue
            if line.find(' REMOVE:') != -1 and line.endswith(':None'):
                continue
            if line.find(' INSERT:') == -1:
                print('Error: unexpected entry: {}'.format(line))
                sys.exit(1)
            pl = reqID = ts = None
            pl_str = ts_str = reqID_str = ''
            idx = line.find('{')
            pl_str = line[idx:]
            pl_str = pl_str.replace("'",'"')
            pl_str = pl_str.replace('\\\\"','"')
            pl_str = pl_str.replace('\\"','"')
            pl_str = pl_str.replace(' "{"',' {"')
            if DEBUG:
                print(pl_str)
            idx = pl_str.find(', "gr_payload": "pl:')
            if idx != -1: #SDK
                idx2 = pl_str.find(']"}"}"}, "reqID":')
                if idx2 == -1:
                    #{"payload": {"S": {"type": "subsegment", "id": "a8574a50b66e46ed", "trace_id": "1-59d6cd8c-f48a3fa1e6b72ce67f895473", "parent_id": "5f38285778fbea09", "start_time": 1507249552.1728623, "gr_payload": "pl:us-west-2:POST:http://httpbin.org/post", "operation": "HTTP"}"}, "reqID": {"S": "e6bdc994-aa2c-11e7-b3dd-abb9cf5b93ae:d74d3049"}, "ts": {"N": "1507249552173"}}
                    idx2 = pl_str.find('}"}, "reqID":')
                    pltmp = '{}}}'.format(pl_str[idx+20:idx2+3])
                    incr = 5
                else:
                    pltmp = pl_str[idx+20:idx2+2]
                    incr = 8
                pl1 = '{}}}}}}}'.format(pl_str[:idx]) #close up the front section to decode it as json
                pldict = json.loads(pl1)
                pldict = pldict['payload']['S']
                myid = pldict['id']
                pid = pldict['parent_id']
                trid = pldict['trace_id']
                start_ts = float(pldict['start_time'])

                pl1 = '{{{}'.format(pl_str[idx2+incr:]) #extract the backend of the string to get the reqID and ts
                pldict = json.loads(pl1)
                reqidx = pldict['reqID']['S'].rfind(':')
                reqID = pldict['reqID']['S'][:reqidx]
                ts = float(pldict['ts']['N'])
                
                rest_dict = processPayload(pltmp,reqID)
                print('SDK dict: {}'.format(rest_dict))
                assert pl_str not in REPEATS
                REPEATS.append(pl)

                #make a child object
                child = {TYPE:'sdk',REQ:reqID,PAYLOAD:rest_dict,TS:start_ts,DUR:0.0,SEQ:seqID,CHILDREN:[]}
                seqID += 1
                #all children are possible event sources at this point
                child[TYPE] = 'sdkT'
                rest,retn = getName(child)
                TRIGGERS[retn].append(child)
                #add the SDK as a child to its entry in REQS
                if reqID in REQS:
                    parent = REQS[reqID]
                else: 
                    parent = SUBREQS[reqID]
                parent[CHILDREN].append(child)
            
            else: #entry
                assert pl_str.startswith('{"payload": {"S": "pl:arn:aws:lambda:')
                #entry that was triggered
                idx = pl_str.find('"}}, "reqID":')
                incr = 4
                if idx == -1:
                    idx = pl_str.find('"}, "reqID":')
                    incr = 3
                pl = pl_str[19:idx]
                plrest = '{{{}'.format(pl_str[idx+incr:])
                pldict = json.loads(plrest)
                reqidx = pldict['reqID']['S'].rfind(':')
                reqID = pldict['reqID']['S'][:reqidx]
                ts = float(pldict['ts']['N'])

                #rest = '{{{}'.format(pl_str[idx+4:])
                assert reqID not in REQS
                trigger,payload = processEventSource(pl)
                ele = {TYPE:'fn',REQ:reqID,PAYLOAD:payload,TS:ts,DUR:0.0,SEQ:seqID,CHILDREN:[]}
                seqID += 1
#HERE CJK what should come back here and what should we store in triggers
                print('(entry) retn: {}'.format(payload))
                if trigger: #this lambda was triggered by an event source
                    assert retn in TRIGGERS
                    plist = TRIGGERS[retn]
                    if len(plist) == 1:
                        parent = plist[0]
                    else:
                        assert True #multiple same events not handled yet
                    parent[CHILDREN].append(ele)
                    SUBREQS[reqID] = ele
                    print('\tadding {} to SUBREQS'.format(reqID))
                else: 
                    print('\tadding {} to REQS'.format(reqID))
                    REQS[reqID] = ele
        

 
##################### main #######################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GammaRay Stream Parser')
    parser.add_argument('fname',action='store',help='filename containing stream data')
    parser.add_argument('hybrid',action='store',help='filename containing xray data')
    args = parser.parse_args()

    if not os.path.isfile(args.hybrid) and not os.path.isdir(args.hybrid): 
        parser.print_help()
        print('\nError: hybrid argument must be a file or a directory containing files ending in .xray')
        sys.exit(1)

    processHybrid(args.hybrid)
    parseIt(args.fname, args.hybrid)
    if DEBUG:
        for ele in SDKS:
            print('SDK: ',ele)
    assert SDKS == []
    makeDotAggregate()

