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
SSID='ssegId'
SSPID='ssegPid'
TRID='traceId'

DEBUG = True
REQS = {}
SUBREQS = {} #for functions triggered (in/)directly by other functions
TRIGGERS = defaultdict(list) #potentially multiple eles in list per key
SDKS = []
SUBSEGS = {} #(sub)segment_id: object

#the only one that has a list is fn (len 9) which includes entry and invoke
SUBSEGS_XRAY = defaultdict(list) #(sub)segment_id: object, length 9 (all but other), and 5 (other)
INITS = {} #reqID:float_duration
eleID = 1
seqID = 1
NODES = {}
##################### getName #######################
def getName(reqObj,INST=False):
    '''Given an object (reqObj), return a unique name for the node
       if INST is True, then add an 8 digit uuid to end of name so that 
       its different from all others (non-aggregated)

       name cannot contain colons as graphviz doesn't handle them in a node name, 
       name can have newlines however
       reqObj = {TYPE:'sdkT',REQ:reqID,SSID:myid,SSPID:pid,TRID:trid,PAYLOAD:rest_dict,TS:start_ts,DUR:0.0,SEQ:seqID,CHILDREN:[]}
       pl = reqObj[PAYLOAD]
       pl['reg'] #region of this function
       pl['name'] #this fn's (callee) name
       pl['tname'] #caller's name, table name, s3 bucket name, snstopic, url
       pl['kn']  #caller reqID, keyname, s3 prefix, sns subject, http_method
       pl['op']' #triggering_operation:source_region
       pl['key'] #unused for fn, key for ddb, filename for s3, unused for sns, unused for http
       pl['rest'] #other info only for event sources

       match is the subportion of name that lets us match SDK calls to triggers

    '''
    
    pl = reqObj[PAYLOAD]
    match = '{}:{}:{}'.format(pl['tname'],pl['kn'],pl['key']) #key is none if unused

    typ = reqObj[TYPE]
    opreg = pl['reg']
    ntoks = pl['op'].split(':')
    op = ntoks[0]
    reg = ntoks[1]
    path = 'ERR'
    if typ == 'fn': 
        name='FN={} {}'.format(pl['name'],pl['reg'])
        if op == 'none':
            match = '{}:{}'.format(pl['tname'],pl['name']) #triggered by a function caller:callee
        elif op == 'Invoke':
            match = '{}:{}'.format(pl['name'],pl['tname']) #triggered by a function caller:callee
        #else use the default match and name above
    else: #sdk
        if op == 'Invoke':
            path = '{}'.format(pl['tname'])
            match = '{}:{}'.format(pl['tname'],pl['name']) #triggered by a function caller:callee
            name='{} {} {}'.format(op,opreg,path)
        elif op.startswith('S3=') or op.startswith('DDB='): #use the default match
            path = '\n{} {}/{}'.format(pl['tname'],pl['kn'],pl['key'])
            name='{} {} {}'.format(op,opreg,path)
        elif op.startswith('SNS=') or op.startswith('HTTP='): #use the default match
            path = '{} {}'.format(pl['tname'],pl['kn'])
            name='{} {} {}'.format(op,opreg,path)
        else:
            print(pl)
            assert False #we shouldn't be here

    if INST:
        name+='_{}'.format(str(uuid.uuid4())[:8]) #should this be requestID?
    return name,match

##################### processDotChild #######################
def processDotChild(dot,req):
    global eleID
    dur = req[DUR]
    name,_ = getName(req)
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

    ''' 
       reqObj = {TYPE:'sdkT',REQ:reqID,SSID:myid,SSPID:pid,TRID:trid,PAYLOAD:rest_dict,TS:start_ts,DUR:0.0,SEQ:seqID,CHILDREN:[]}
       pl = reqObj[PAYLOAD]
       pl['reg'] #region of this function
       pl['name'] #this fn's (callee) name
       pl['tname'] #caller's name, table name, s3 bucket name, snstopic, url
       pl['kn']  #caller reqID, keyname, s3 prefix, sns subject, http_method
       pl['op']' #triggering_operation:source_region
       pl['key'] #unused for fn, key for ddb, filename for s3, unused for sns, unused for http
       pl['rest'] #other info only for event sources
       REQS holds all of the gammaray nodes (each potentially having CHILDREN)
       REQS holds all of the gammaray nodes (each potentially having CHILDREN)
       SUBSEGS holds all nodes by SSID
    '''
    for key in REQS:
        req = REQS[key]
        pl = req[PAYLOAD]
        name,_ = getName(req)
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
    ''' returns True/False, payload as dict:
        	    # for different operations, order is: Fn, DDB, S3, SNS, HTTP with .amazonaws.com in url
        retn['reg'] #region of this function
        retn['name'] #this fn's (callee) name
        retn['tname'] #caller's name, table name, s3 bucket name, snstopic, url
        retn['kn']  #caller reqID, keyname, s3 prefix, sns subject, http_method
        retn['op']' #triggering_operation:source_region
        retn['key'] #unused for fn, key for ddb, filename for s3, unused for sns, unused for http
        retn['rest'] #other info only for event sources
    '''
    toks = pl.split(':')
    retn = {'name': toks[7], 'reg': toks[4], 'rest':'none', 'key':'none', 'kn':'none'} #potentially unused keys
    triggered = False
    if pl.startswith('pl:arn:aws:lambda:') and (len(toks) == 8 or pl.endswith(':es:ext:invokeCLI')): #normal Invoke with unknown trigger
        retn['tname'] = 'none'
        retn['op'] = 'none:{}'.format(toks[4])
        pass
    elif ':es:lib:invokeCLI:' in pl: #Invoke trigger
        triggered = True
        #pl:arn:aws:lambda:us-west-2:XXX:function:emptyB:es:lib:invokeCLI:FnInvokerPyB:ed086648-aa47-11e7-a1cd-4dab0b1999f4
        retn['op'] = 'Invoke:{}'.format(toks[4]) #triggering_operation:source_region
        retn['tname'] = toks[11] #caller's name
        retn['kn'] = toks[12] #caller reqID
        #key 'key', 'rest' not used

    elif ':ddb:' in pl: #DDB update trigger
        triggered = True
        #pl:arn:aws:lambda:us-west-2:XXX:function:DBSyncPyB:esARN:arn:aws:dynamodb:us-west-2:XXX:table/image-proc-B/stream/2017-10-05T21:42:44.663:es:ddb:keys:id:{"S": "imgProc/d1.jpg1428"}:op:INSERT
	#get tablename
        assert pl.find('esARN:') != -1
        tmp_tname = toks[14].split('/')
        retn['tname'] = tmp_tname[1] #table name
        retn['kn'] = toks[20] #key name
        retn['key'] = toks[22].strip(' "}') #key
        retn['rest'] = '{}:{}:{}'.format(tmp_tname[3],toks[15],toks[16]) #stream ID
        retn['op'] = 'DDB={}:{}'.format(toks[24],toks[12]) #triggering_op:source_region
        print('here! {}'.format(retn))
    else:
        print(pl)
        assert False
        #for HTTP the source region must be the same as this functions region because APIGW can only invoke functions in its region
    return triggered,retn

##################### processPayload #######################
def processPayload(pl,reqID): #about to do something that can trigger a lambda function
    ''' returns payload as dict:
        	    # for different operations, order is: Fn, DDB, S3, SNS, HTTP with .amazonaws.com in url
        retn['reg'] #region of operation target
        retn['name'] #this fn's name
        retn['tname'] #callee's name, table name, s3 bucket name, snstopic, url
        retn['kn']  #unused for fn, keyname, s3 prefix, sns subject, unused for http
        retn['op']' #triggering_operation:current_region
        retn['key'] #unused for fn, key for ddb, filename for s3, unused for sns, unused for http
    '''
    #PutItem:us-west-2:TableName:image-proc-B:Item:{"id": "imgProc/d1.jpg0b92", "labels": "[{"Name": "Animal", "Confidence": 96.52117156982422}, {"Name": "Gazelle", "Confidence": 96.52117156982422}, {"Name": "Impala", "Confidence": 96.52117156982422}, {"Name": "Mammal", "Confidence": 96.52117156982422}, {"Name": "Wildlife", "Confidence": 96.52117156982422}, {"Name": "Deer", "Confidence": 91.72703552246094}]"}
    #ops include [ 'PutItem', 'UpdateItem', 'DeleteItem', 'BatchWriteItem', 'PutObject', 'DeleteObject', 'PostObject', 'Publish', 'Invoke' ]
    pl = pl.strip('"}')
    if DEBUG: 
        print('ppayload: {}'.format(pl))

    #get the enclosing functions details
    if reqID in REQS:
        me = REQS[reqID]
    else: 
        me = SUBREQS[reqID]
    toks = pl.split(':')
    current_region = me['pl']['reg']
    nm = me['pl']['name']
    retn = {'name': nm, 'reg': toks[1], 'rest':'none', 'key':'none', 'kn':'none'} #potentially unused keys

    if pl.startswith('PutItem:'):
        retn['op'] = 'DDB=PutItem:{}'.format(current_region)
        rest = pl[8:]
        idx = rest.find(':TableName:')
        assert idx != -1
        idx2 = rest.find(':Item:')
        assert idx2 != -1
        retn['tname'] = rest[idx+11:idx2]
        data = rest[idx2+7:] #7 to get past the {
        toks = data.split(': ')
        retn['kn'] = toks[0].strip('"')
        toks = toks[1].split(' ')
        retn['key'] = toks[0].strip('",')
        #'rest' is unused

    elif pl.startswith('UpdateItem:'):
        retn['op'] = 'DDB=UpdateItem'
        print(pl)
        sys.exit(1)

    elif pl.startswith('DeleteItem:'):
        retn['op'] = 'DDB=DeleteItem'
        print(pl)
        sys.exit(1)

    elif pl.startswith('BatchWriteItem:'):
        retn['op'] = 'DDB=BatchWriteItem'
        print(pl)
        sys.exit(1)

    elif pl.startswith('PutObject:'):
        retn['op'] = 'S3=PutObject'
        print(pl)
        sys.exit(1)

    elif pl.startswith('DeleteObject:'):
        retn['op'] = 'S3=DeleteObject'
        print(pl)
        sys.exit(1)

    elif pl.startswith('PostObject:'):
        retn['op'] = 'S3=PostObject'
        print(pl)
        sys.exit(1)

    elif pl.startswith('Publish:'):
        retn['op'] = 'SNS=Publish'
        print(pl)
        sys.exit(1)

    elif pl.startswith('Invoke:'):
        #Invoke:us-west-2:FunctionName:arn:aws:lambda:us-west-2:XXX:function:emptyB:InvocationType:Event
        retn['op'] = 'Invoke:{}'.format(current_region)
        toks = pl.split(':')
        retn['reg'] = toks[1] #region of both
        retn['tname'] = toks[9]  #callee name
        retn['kn'] = reqID  #caller reqID
        retn['rest'] = '{}'.format(toks[11]) #invocationType
        assert toks[1] == toks[6] #make sure they are in the same region
        #key 'key' not used

    elif pl.startswith('HTTP:'):
        #HTTP:us-west-2:POST:http://httpbin.org/post
        #API Gateway url: https://6w1s7kyypi.execute-api.us-west-2.amazonaws.com/beta
        url = toks[3]
        assert url.startswith('http')
        incr = 7
        if url.startswith('https://'):
            incr += 1
        if url.find('amazonaws.com') != -1 and url.find('execute_api') != -1:
            #url is an api-gateway and thus potential trigger
            url = url[incr:] 
            urltoks = url.split('.')
            retn['op'] = 'HTTP:{}'.format(current_region)
            retn['reg'] = urltoks[2] #region (api gateway urls can only invoke functions in the same region)
            retn['tname'] = url
            retn['kn'] = toks[2] #method
            #key 'key' not used
        else:
            #todo: turn this on once old logs are gone
            #assert False
            retn = None
    else:
        assert False

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
                xray_str = None
                trid=myid=tname=op=reg=key=keyname=parent_reqID='unknown'
                doc_dict = json.loads(seg['Document'])
                print('parentid? {}'.format(doc_dict))
                #timings startup = AL:Dwell+AL:Attempt+ALFN:Initialization(if any)
                #timings execution = ALFN duration
                #timings for sdks are in subsegments under ALFN
                if 'origin' in doc_dict: #AWS::Lambda (parent of Dwell,Attempts)
                    name = doc_dict['name']
                    myid = seg['Id']
                    keyname = doc_dict['trace_id']
                    origin = doc_dict['origin']
                    start = float(doc_dict['start_time'])
                    end = float(doc_dict['end_time'])
                    aws = doc_dict['aws']

                    if origin == 'AWS::Lambda': #AWS::Lambda (parent of Dwell,Attempts)
                        assert 'resource_arn' in aws
                        parent_reqID = tname = aws['request_id']
                        myarn = doc_dict['resource_arn']
                        toks = myarn.split(':') #arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyB
                        reg = toks[3] #region
                        name = toks[6] #function name
                        key = toks[4] #account number
                        xray_str = '{}:AWS_Lambda:{}:{}:{}:{}:{}:{}:False'.format(name,reg,tname,keyname,key,start,end)
                        #step through subsegments (Dwell and Attempt)
                        #record time spent in startup
                        #record tuple using dwell's ssid


                    elif origin == 'AWS::Lambda:Function': #AWS::Lambda:Function (parent of Initialization,requests, and SDKs)
                        myarn = aws['function_arn']
                        toks = myarn.split(':') #arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyB
                        name = toks[6]
                        reg = toks[3]
                        #tname,key unused
                        xray_str = '{}:AWS_Lambda_FN:{}:{}:{}:{}:{}:{}:False'.format(name,reg,tname,keyname,key,start,end)
                        #update tuple
                        #step through subsegments (requests, sdks) 
                        #record time spent in requests+sdks
                    else:
                        pass #skip all others as they are repeats of SDKs and requests

                    if xray_str: #valid if we set it above
                        if DEBUG:
                            print('xray {} {}'.format(myid,xray_str))
                        assert myid not in SUBSEGS_XRAY
                        SUBSEGS_XRAY[myid].append(xray_str) 
    
                    parent_id = myid #the parent of subsegments is this outer segment
                    if 'subsegments' in doc_dict:
                        for subs in doc_dict['subsegments']:
                            xray_str = None
                            trid=myid=tname=op=reg=key=keyname='unknown'
                            subid = subs['id']
                            name = subs['name']
                            err = 'False'
                            if 'error' in subs:
                                err = str(subs['error'])
                            start = subs['start_time']
                            end = subs['end_time']
                            if 'aws' in subs:
                                aws = subs['aws']
                                if 'function_arn' in aws:
                                    fn = aws['function_arn']
                                if 'trace_id' in aws:
                                    trid = aws['trace_id']
                                if 'operation' in aws:
                                    op = aws['operation']
                                if 'request_id' in aws:
                                    tname = aws['request_id'] #tname holds reqID (HTTP)
                                if 'table_name' in aws:
                                    tname = aws['table_name'] #tname holds TableName (DDB)
                                if 'region' in aws:
                                    reg = aws['region']
                                if 'http' in subs and 'response' in subs['http']:
                                    keyname = subs['http']['response']['status']
                                skip = False
                                if 'gr_payload' in aws:
                                    pl = aws['gr_payload']
                                    idx = pl.find(':Item:{')
                                    #idx3 = pl.find(':FunctionName:')
                                    if idx != -1: #DDB 
                                        idx2 = pl.find(':',idx+7)
                                        keyname = pl[idx+7:idx2].strip('"\' ') #DDB keyname
                                        idx = pl.find(',',idx2+1)
                                        key = pl[idx2+1:idx].strip('"\' ') #DDB key
                                    #elif idx3 != -1: #Lambda:Invoke handled outside (no gr_payload)
                                        ##payload:arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyB:FunctionName:arn:aws:lambda:us-west-2:XXX:function:DBModPyB:InvocationType:Event:Payload
                                        #idx = pl.find(':',idx3+29)
                                        #reg = pl[idx3+29:idx]
                                        #idx = pl.find(':function:',idx3+29)
                                        #idx2 = pl.find(':',idx+10)
                                        #tname = pl[idx+10:idx2] #function name
                                        #idx = pl.find(':InvocationType:')
                                        #idx2 = pl.find(':',idx+16)
                                        #keyname= pl[idx+16:idx2] #Event (Async) or RequestResponse (Sync)
                                        #key = aws['request_id'] #request ID of invoke call
                                    elif ':TopicArn:arn:aws:sns:' in pl: #SNS
                                        idx = pl.find(':TopicArn:arn:aws:sns:')
                                        pl_str = pl[idx+22:].split(':')
                                        reg = pl_str[0]
                                        tname = pl_str[2]#topicARN
                                        keyname = pl_str[4] #Subject
                                        idx = pl.find(':Message:') 
                                        key = pl[idx+9:idx+39] #first 30 chars after Message:
                                    elif ':Bucket:' in pl: #S3
                                        idx = pl.find(':Bucket:')
                                        pl_str = pl[idx+8:].split(':')
                                        tname = pl_str[0] #bucket name
                                        keyname = pl_str[2] #keyname
                                    else:
                                        print('Unhandled GammaRay payload: {}'.format(doc_dict))
                                        assert False
                                        skip = True #this will handle it if asserts are removed

                                elif name == 'Lambda': #Lambda:Invoke  //no gr_payload
                                    print('SDK Invoke: {}'.format(pl))
                                    key = aws['request_id']
                                    keyname = str(subs['error'])
                                    #HERE

                                elif name == 'Initialization': #container setup time //no gr_payload
                                    assert tname == 'unknown' and 'function_arn' in aws
                                    toks = fn.split(':') #arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyB
                                    reg = toks[3] #function's region
                                    tname = toks[6] #function name
                                    assert parent_id in SUBSEGS_XRAY
                                    dwell = SUBSEGS_XRAY[parent_id][0]
                                    toks = dwell.split(':')
                                    assert toks[1] not in INITS
                                    INITS[toks[1]] = end-start #record duration to add to overhead of FN invocation
                                    skip = True 
                                else:
                                    print('missed subsegment: {}'.format(subs))
                                    assert False
                                    skip = True #this will handle it if asserts are removed

                                if not skip:
                                    #length 9 = sdk subsegment
                                    xray_str = '{}:{}:{}:{}:{}:{}:{}:{}:{}'.format(name,op,reg,tname,keyname,key,start,end,err)
                            else:
                                if name == 'requests':
                                    assert 'http' in subs
                                    http = subs['http']
                                    url = http['request']['url'][7:] #trim off the http:// chars
                                    op = http['request']['method']
                                    status = http['response']['status']
                                    #API Gateway url: https://6w1s7kyypi.execute-api.us-west-2.amazonaws.com/beta
                                    if 'amazonaws.com' in url:
                                        toks = url.split('.')
                                        assert toks[3] == 'amazonaws'
                                        reg = toks[2]
                                    
                                    #length 9 = requests subsegment
                                    xray_str = '{}:{}:{}:{}:{}:{}:{}:{}:{}'.format(name,op,reg,tname,url,status,start,end,err)
                                elif 'Dwell Time' not in name: #Dwell time already in encapsulated in AWS::Lambda time
                                    #however we need it to get to the parent's request id
                                    assert parent_reqID != 'unknown'
                                    xray_str = '{}:{}:{}:{}:{}'.format(name,parent_reqID,start,end,err)
                                else:
                                    #length 5 other subsegment
                                    xray_str = '{}:{}:{}:{}:{}'.format(name,parent_id,start,end,err)
                            if xray_str: #valid if we set it above
                                if DEBUG:
                                    print('xray {} parent {} payload {}'.format(subid,parent_id,xray_str))
                                assert subid not in SUBSEGS_XRAY
                                SUBSEGS_XRAY[subid].append(xray_str) #length 9 (all but other), or 4 (other)
                else:
                    pass #can skip this as they are repeats
                    #print(doc_dict) #for debugging
                    
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
                if not rest_dict:
                    continue
                print('SDK dict: {}'.format(rest_dict))

                #make a child object-- all are possible event sources at this point (B config)
                child = {TYPE:'sdkT',REQ:reqID,SSID:myid,SSPID:pid,TRID:trid,PAYLOAD:rest_dict,TS:start_ts,DUR:0.0,SEQ:seqID,CHILDREN:[]}
                seqID += 1
                #assert myid not in SUBSEGS
                #SUBSEGS[myid] = child
                assert myid in SUBSEGS_XRAY
                l_subsegs = SUBSEGS_XRAY[myid]
                assert len(l_subsegs) == 1
                xray_data = l_subsegs[0]
                toks = xray_data.split(':') #length 9 for sdk, name:op:reg:name2:keyname:key:start:end:err
                assert len(toks) == 9
                print(xray_data)
                child[DUR] = float(xray_data[7]) - float(xray_data[6])

                _,match = getName(child)
                print('mch: {}'.format(match))
                TRIGGERS[match].append(child)
                #add the SDK as a child to its entry in REQS
                if reqID in REQS:
                    parent = REQS[reqID]
                else: 
                    parent = SUBREQS[reqID]
                parent[CHILDREN].append(child)
                #update the parent's SSID (we didn't know its SSID when it came in) and add it to SUBSEGS
                pssid = parent[SSID]
                if pssid == 'none':
                    parent[SSID] = pid
                    #assert pid not in SUBSEGS
                    #SUBSEGS[pid] = parent
                    assert pid in SUBSEGS_XRAY
                    l_subsegs = SUBSEGS_XRAY[pid]
                    assert len(l_subsegs) == 2
                    psum = 0.0
                    for xray_data in l_subsegs:
                        toks = xray_data.split(':') #length 9 for fn, name:AWS_Lambda|AWS_Lambda_FN:reg:name2:keyname:key:start:end:err
                        assert len(toks) == 9
                        psum += (float(xray_data[7]) - float(xray_data[6]))
                        tname = xray_data[3]
                        op = xray_data[1]
                        if op == 'AWS_Lambda':
                            assert tname == reqID
                    parent[DUR] = psum
                
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

                assert reqID not in REQS
                trigger,payload = processEventSource(pl)
                ele = {TYPE:'fn',REQ:reqID,SSID:'none',SSPID:'none',TRID:'none',PAYLOAD:payload,TS:ts,DUR:0.0,SEQ:seqID,CHILDREN:[]}
                seqID += 1
                if trigger: #this lambda was triggered by an event source
                    _,match = getName(ele)
                    assert match in TRIGGERS
                    plist = TRIGGERS[match]
                    if len(plist) == 1:
                        parent = plist[0]
                    else:
                        assert False #multiple same events not handled yet
                    parent[CHILDREN].append(ele)
                    SUBREQS[reqID] = ele
                else: 
                    REQS[reqID] = ele

##################### processHybridOrig  #######################
def processHybridOrig(fname):
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
                xray_str = None
                trid=myid=tname=op=reg=key=keyname=parent_reqID='unknown'
                doc_dict = json.loads(seg['Document'])
                print('parentid? {}'.format(doc_dict))
                name = doc_dict['name']
                myid = seg['Id']
                if 'trace_id' in doc_dict:
                    trid = doc_dict['trace_id']
                start = doc_dict['start_time']
                end = doc_dict['end_time']
                #timings startup = AL:Dwell+AL:Attempt+ALFN:Initialization(if any)
                #timings execution = ALFN duration
                #timings for sdks are in subsegments under ALFN
                if 'aws' in doc_dict:
                    aws = doc_dict['aws']
                    tname = op = reg = pl = 'unknown'
                    if 'operation' in aws:
                        op = aws['operation']
                    origin = doc_dict['origin']
                    if origin == 'AWS::Lambda' and 'resource_arn' in doc_dict: #AWS::Lambda (parent of Dwell,Attempts)
                        keyname = trid #trace id
                        if 'request_id' in aws:
                            tname = aws['request_id']
                            parent_reqID = tname
                        myarn = doc_dict['resource_arn']
                        toks = myarn.split(':') #arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyB
                        reg = toks[3] #region
                        name = toks[6] #function name
                        key = toks[4] #account number
                        #startup time is given by start/end (it encapsulates Dwell subsegment so no 
                        #need to record it below)
                        xray_str = '{}:AWS_Lambda:{}:{}:{}:{}:{}:{}:False'.format(name,reg,tname,keyname,key,start,end)
                        if DEBUG:
                            print('\t',xray_str)
                            print('\ttrid: {}'.format(trid))
                    else:
                        if 'function_arn' in aws: #AWS::Lambda::Function (won't have a resource_arn)
                            keyname = trid #trace id
                            myarn = aws['function_arn']
                            toks = myarn.split(':') #arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyB
                            name = toks[6]
                            reg = toks[3]
                            #tname,key unused
                            xray_str = '{}:AWS_Lambda_FN:{}:{}:{}:{}:{}:{}:False'.format(name,reg,tname,keyname,key,start,end)
                            if DEBUG:
                                print('\t',xray_str)
                                print('\ttrid: {}'.format(trid))
                        else:
                            pass #can skip this as data is repeated

                    if xray_str: #valid if we set it above
                        if DEBUG:
                            print('xray {} {}'.format(myid,xray_str))
                        assert myid not in SUBSEGS_XRAY
                        SUBSEGS_XRAY[myid].append(xray_str) 
    
                    parent_id = myid #the parent of subsegments is this outer segment
                    if 'subsegments' in doc_dict:
                        for subs in doc_dict['subsegments']:
                            xray_str = None
                            trid=myid=tname=op=reg=key=keyname='unknown'
                            subid = subs['id']
                            name = subs['name']
                            err = 'False'
                            if 'error' in subs:
                                err = str(subs['error'])
                            start = subs['start_time']
                            end = subs['end_time']
                            if 'aws' in subs:
                                aws = subs['aws']
                                if 'function_arn' in aws:
                                    fn = aws['function_arn']
                                if 'trace_id' in aws:
                                    trid = aws['trace_id']
                                if 'operation' in aws:
                                    op = aws['operation']
                                if 'request_id' in aws:
                                    tname = aws['request_id'] #tname holds reqID (HTTP)
                                if 'table_name' in aws:
                                    tname = aws['table_name'] #tname holds TableName (DDB)
                                if 'region' in aws:
                                    reg = aws['region']
                                if 'http' in subs and 'response' in subs['http']:
                                    keyname = subs['http']['response']['status']
                                skip = False
                                if 'gr_payload' in aws:
                                    pl = aws['gr_payload']
                                    idx = pl.find(':Item:{')
                                    #idx3 = pl.find(':FunctionName:')
                                    if idx != -1: #DDB 
                                        idx2 = pl.find(':',idx+7)
                                        keyname = pl[idx+7:idx2].strip('"\' ') #DDB keyname
                                        idx = pl.find(',',idx2+1)
                                        key = pl[idx2+1:idx].strip('"\' ') #DDB key
                                    #elif idx3 != -1: #Lambda:Invoke handled outside (no gr_payload)
                                        ##payload:arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyB:FunctionName:arn:aws:lambda:us-west-2:XXX:function:DBModPyB:InvocationType:Event:Payload
                                        #idx = pl.find(':',idx3+29)
                                        #reg = pl[idx3+29:idx]
                                        #idx = pl.find(':function:',idx3+29)
                                        #idx2 = pl.find(':',idx+10)
                                        #tname = pl[idx+10:idx2] #function name
                                        #idx = pl.find(':InvocationType:')
                                        #idx2 = pl.find(':',idx+16)
                                        #keyname= pl[idx+16:idx2] #Event (Async) or RequestResponse (Sync)
                                        #key = aws['request_id'] #request ID of invoke call
                                    elif ':TopicArn:arn:aws:sns:' in pl: #SNS
                                        idx = pl.find(':TopicArn:arn:aws:sns:')
                                        pl_str = pl[idx+22:].split(':')
                                        reg = pl_str[0]
                                        tname = pl_str[2]#topicARN
                                        keyname = pl_str[4] #Subject
                                        idx = pl.find(':Message:') 
                                        key = pl[idx+9:idx+39] #first 30 chars after Message:
                                    elif ':Bucket:' in pl: #S3
                                        idx = pl.find(':Bucket:')
                                        pl_str = pl[idx+8:].split(':')
                                        tname = pl_str[0] #bucket name
                                        keyname = pl_str[2] #keyname
                                    else:
                                        print('Unhandled GammaRay payload: {}'.format(doc_dict))
                                        assert False
                                        skip = True #this will handle it if asserts are removed

                                elif name == 'Lambda': #Lambda:Invoke  //no gr_payload
                                    print('SDK Invoke: {}'.format(pl))
                                    key = aws['request_id']
                                    keyname = str(subs['error'])
                                    #HERE

                                elif name == 'Initialization': #container setup time //no gr_payload
                                    assert tname == 'unknown' and 'function_arn' in aws
                                    toks = fn.split(':') #arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyB
                                    reg = toks[3] #function's region
                                    tname = toks[6] #function name
                                    assert parent_id in SUBSEGS_XRAY
                                    dwell = SUBSEGS_XRAY[parent_id][0]
                                    toks = dwell.split(':')
                                    assert toks[1] not in INITS
                                    INITS[toks[1]] = end-start #record duration to add to overhead of FN invocation
                                    skip = True 
                                else:
                                    print('missed subsegment: {}'.format(subs))
                                    assert False
                                    skip = True #this will handle it if asserts are removed

                                if not skip:
                                    #length 9 = sdk subsegment
                                    xray_str = '{}:{}:{}:{}:{}:{}:{}:{}:{}'.format(name,op,reg,tname,keyname,key,start,end,err)
                            else:
                                if name == 'requests':
                                    assert 'http' in subs
                                    http = subs['http']
                                    url = http['request']['url'][7:] #trim off the http:// chars
                                    op = http['request']['method']
                                    status = http['response']['status']
                                    #API Gateway url: https://6w1s7kyypi.execute-api.us-west-2.amazonaws.com/beta
                                    if 'amazonaws.com' in url:
                                        toks = url.split('.')
                                        assert toks[3] == 'amazonaws'
                                        reg = toks[2]
                                    
                                    #length 9 = requests subsegment
                                    xray_str = '{}:{}:{}:{}:{}:{}:{}:{}:{}'.format(name,op,reg,tname,url,status,start,end,err)
                                elif 'Dwell Time' not in name: #Dwell time already in encapsulated in AWS::Lambda time
                                    #however we need it to get to the parent's request id
                                    assert parent_reqID != 'unknown'
                                    xray_str = '{}:{}:{}:{}:{}'.format(name,parent_reqID,start,end,err)
                                else:
                                    #length 5 other subsegment
                                    xray_str = '{}:{}:{}:{}:{}'.format(name,parent_id,start,end,err)
                            if xray_str: #valid if we set it above
                                if DEBUG:
                                    print('xray {} parent {} payload {}'.format(subid,parent_id,xray_str))
                                assert subid not in SUBSEGS_XRAY
                                SUBSEGS_XRAY[subid].append(xray_str) #length 9 (all but other), or 4 (other)
                else:
                    pass #can skip this as they are repeats
                    #print(doc_dict) #for debugging
                    
    print('DONE')
            
   
 
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

