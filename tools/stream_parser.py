import json,time,os,sys,argparse,statistics,ast,uuid
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
START='dur'
CHILDREN='children'
SSID='ssegId'

DEBUG = False
REQS = {}
SUBREQS = {} #for functions triggered (in/)directly by other functions
TRIGGERS = defaultdict(list) #potentially multiple eles in list per key

#the only one that has a list is fn (len 8) which includes entry and invoke
SUBSEGS_XRAY = {} 
XRAY_REQS = {} #(startup_duration,container_started,exec_duration) container_started is True/False, rest are floats
seqID = 1
NODES = {}
##################### getName #######################
def getName(reqObj,AGG=True):
    '''Given an object (reqObj), return a unique name for the node
       if AGG is False (instance has been requested), then add the request ID to the name so that 
       its different from all others (non-aggregated)

       name cannot contain colons as graphviz doesn't handle them in a node name, 
       name can have newlines however
       reqObj = {TYPE:'sdkT',REQ:reqID,SSID:myid,PAYLOAD:rest_dict,TS:start_ts,DUR:0.0,START:0.0,SEQ:seqID,CHILDREN:[]}
       pl = reqObj[PAYLOAD]
       pl['reg'] #region of this function
       pl['name'] #this fn's (callee) name
       pl['tname'] #caller's name, table name, s3 bucket name, snstopic, url
       pl['kn']  #caller reqID, keyname, s3 prefix, sns subject, http_method
       pl['op']' #triggering_operation:source_region
       pl['key'] #unused for fn, key for ddb, filename for s3, unused for sns, unused for http
       pl['rest'] #other info only for event sources

       match is the subportion of name that lets us match SDK calls to triggers

       NONTRIGGER in name = nonSDK => gray
       NOXRAYDATA in name = 'NOXRAYDATA' in rest => blue
       ERR in name = error in 'rest' => red

       PLEASE NOTE, DO NOT! PUT A COLON IN THE NAME STRING THAT IS RETURNED
       IT CAUSES DOT/GRAPHVIZ PROBLEMS WHEN USED IN THE NODE NAME (EDGES WILL NOT BE CREATED CORRECTLY)

    '''
    
    pl = reqObj[PAYLOAD]
    match = '{}:{}:{}'.format(pl['tname'],pl['kn'],pl['key']) #key is none if unused
    color = 'black'
    typ = reqObj[TYPE]
    opreg = pl['reg']
    ntoks = pl['op'].split(':')
    op = ntoks[0]
    if len(ntoks) > 1:
        reg = ntoks[1]
    else:
        reg = 'unknown'
    path = 'ERR'
    if typ == 'fn': #function entry
        name='FN={} {}'.format(pl['name'],pl['reg'])
        if op == 'none':
            match = '{}:{}'.format(pl['tname'],pl['name']) #unknown trigger
        elif op == 'Invoke':
            match = '{}:{}:{}:{}'.format(pl['name'],reqObj['req'],pl['tname'],pl['kn']) #triggered by a function callee(this_fn):caller
        #else use the default match and name above
    elif typ == 'sdkT': #sdk trigger
        if op == 'Invoke':
            path = '{} {}'.format(pl['tname'],pl['kn'])
            match = '{}:{}:{}:{}'.format(pl['tname'],pl['kn'],pl['name'],reqObj['req']) #triggered by a function callee:caller(this_fn)
            name='{} {} {}'.format(op,opreg,path)
        elif op.startswith('S3=') or op.startswith('DynamoDB='): #use the default match
            path = '\n{} {}'.format(pl['tname'],pl['kn'])
            name='{} {} {}'.format(op,opreg,path)
        elif op.startswith('SNS=') or op.startswith('HTTP='): #use the default match
            path = '{} {}'.format(pl['tname'],pl['kn'])
            name='{} {} {}'.format(op,opreg,path)
        else:
            print(pl)
            assert False #we shouldn't be here
    else:  #sdk nontrigger
        color = 'gray'

    if not AGG:
        #name+='_{}'.format(str(uuid.uuid4())[:8]) #should this be requestID?
        name+='\n{}'.format(reqObj['req']) #should this be requestID?

    if pl['rest'].find('NOXRAYDATA') != -1:
        color = 'yellow'
    elif pl['rest'].find(':error:True') != -1:
        print('WARNING, node error: {}'.format(reqObj))
        color = 'red'

    return name,match,color

##################### processDotChild #######################
def processDotChild(dot,req,dot_agg=False):
    global NODES
    dur = req[DUR]
    name,_,color= getName(req,dot_agg)
    totsum = dur
    count = 1
    if name in NODES:
        (t,c) = NODES[name]
        totsum+=t
        count += c
    NODES[name] = (totsum,count)
    avg = totsum/count 
    nodename='{}\navg: {:0.1f}ms'.format(name,avg)
    if color == 'gray': #non-sdk
        dot.node(name,nodename,fillcolor=color,style='filled')
    else:
        dot.node(name,nodename,color=color,shape='octagon')
    for child in req[CHILDREN]:
        child_name = processDotChild(dot,child)
        dot.edge(name,child_name)
    return name

##################### makeDot #######################
def makeDot(dot_agg=False,dot_include_nontriggers=False):
    global NODES
    mystr = ''
    if dot_agg:
        mystr = '.agg' 
    dot = Digraph(comment='gammaRayGraph{}'.format(mystr),format='pdf')
    agent_name = "Clients"
    dot.node(agent_name,agent_name)
    agent_edges = []

    ''' 
       reqObj = {TYPE:'sdkT',REQ:reqID,SSID:myid,PAYLOAD:rest_dict,TS:start_ts,DUR:0.0,START:0.0,SEQ:seqID,CHILDREN:[]}
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
        name,_,color = getName(req,dot_agg)
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
        if color == 'gray': #non-sdk
            dot.node(name,nodename,fillcolor=color,style='filled')
        else:
            dot.node(name,nodename,color=color,shape='octagon')
        if name not in agent_edges: 
            dot.edge(agent_name,name)
            agent_edges.append(name)

        for child in req[CHILDREN]:
            child_name = processDotChild(dot,child,dot_agg)
            dot.edge(name,child_name)

    if dot_include_nontriggers:
        processReads(dot,dot_agg)

    dot.render('gragggraph', view=True)
    return

##################### processEventSource #######################
def processReads(dot,dot_agg):
    global NODES
    '''include xray reads in dot graph (non-event-sources)'''
    #trigger ops to skip [ 'PutItem', 'UpdateItem', 'DeleteItem', 'BatchWriteItem', 'PutObject', 'DeleteObject', 'PostObject', 'Publish', 'Invoke' ]
    for ele in SUBSEGS_XRAY:
        if ':PutItem:' in SUBSEGS_XRAY[ele]:
            continue
        if ':UpdateItem:' in SUBSEGS_XRAY[ele]:
            continue
        if ':DeleteItem:' in SUBSEGS_XRAY[ele]:
            continue
        if ':BatchWriteItem:' in SUBSEGS_XRAY[ele]:
            continue
        if ':PutObject:' in SUBSEGS_XRAY[ele]:
            continue
        if ':DeleteObject:' in SUBSEGS_XRAY[ele]:
            continue
        if ':PostObject:' in SUBSEGS_XRAY[ele]:
            continue
        if ':Publish:' in SUBSEGS_XRAY[ele]:
            continue
        if ':Invoke:' in SUBSEGS_XRAY[ele]:
            continue
        if SUBSEGS_XRAY[ele].startswith('requests:'):
            if '.amazonaws.com' in SUBSEGS_XRAY[ele]:
                continue
        xray = SUBSEGS_XRAY[ele]
        toks = xray.split(':')
        toklen = len(toks)
        reqID = toks[toklen-1] #last component is requestID
        if reqID in REQS:
            parent = REQS[reqID]
        else: 
            parent = SUBREQS[reqID]

        myid = ele
        parentname,_,_= getName(parent,dot_agg)
        parentname,_,_= getName(parent,dot_agg)

        #name is 2 lines: svc=op region\nother other
        dur = float(toks[6])
        ERR = False

        if toks[0] == 'requests':
            #290026a7b3874e8d requests:POST:unknown:unknown:httpbin.org/post:200:0.41441774368286133:False:ff12e189-ab9a-11e7-84e2-6758c617c45d
            if toks[5] != '200':
                ERR = True
            name = '{}={} {}'.format(toks[0],toks[1],toks[4])

        else:
            #9cf56c565aa0431d DynamoDB:GetItem:us-west-2:image-proc-B:200:unknown:0.6778364181518555:False:d8599d60-85c4-47c0-8684-f589accc0dab
            if toks[4] != '200':
                ERR = True
            name = '{}={} {}\n{}'.format(toks[0],toks[1],toks[2],toks[3])
            if toks[0] == 'S3' and dot_agg:
                ##S3:GetObject:us-west-2:B36DBE0CEA80DDA5:200:unknown:0.03930234909057617:False:b97b3871-ac79-11e7-83ab-d1249a09b700
                name = '{}={} {}'.format(toks[0],toks[1],toks[2])

        #aggregate the timings
        totsum = dur
        count = 1
        if name in NODES:
            (t,c) = NODES[name]
            totsum+=t
            count += c
        NODES[name] = (totsum,count)
        avg = totsum/count 
        nodename='{}\navg: {:0.1f}ms'.format(name,avg)

        if ERR:
            print('WARNING, node error: {}'.format(nodename))
            dot.node(name,nodename,color='red',fillcolor='gray',style='filled')
        else:
            dot.node(name,nodename,fillcolor='gray',style='filled')
        dot.edge(parentname,name)
        
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
        retn['op'] = 'DynamoDB={}:{}'.format(toks[24],toks[12]) #triggering_op:source_region
    elif ':s3:bkt:' in pl: #S3 Object trigger (same region as triggered fn)
        triggered = True
        #pl:arn:aws:lambda:us-west-2:443592014519:function:reducerCoordinatorB:es:s3:bkt:spot-mr-bkt-b:key:job8000/task/mapper/0:op:ObjectCreated:Put
        toks = pl.split(':')
        retn['tname'] = toks[11] #bucket name
        retn['kn'] = toks[13] #full file name
        retn['op'] = 'S3={}_{}:{}'.format(toks[15],toks[16],toks[4])
        #key not used
    elif ':es:sns:' in pl: #SNS Object trigger (same region as triggered fn)
        triggered = True
        #pl:arn:aws:lambda:us-west-2:443592014519:function:S3ModPyB:es:sns:sub:sub1:op:arn:aws:sns:us-west-2:443592014519:topicB
        toks = pl.split(':')
        retn['reg'] = toks[16] #region of topic
        retn['tname'] = toks[18] #topic
        retn['kn'] = toks[11] #subject
        retn['op'] = 'SNS={}:{}'.format(toks[15],toks[16])
        #key not used
    else:
        print('processEventSource<unsupported op>',pl)
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
        retn['rest'] #for errors, other if needed
    '''
    #PutItem:us-west-2:TableName:image-proc-B:Item:{"id": "imgProc/d1.jpg0b92", "labels": "[{"Name": "Animal", "Confidence": 96.52117156982422}, {"Name": "Gazelle", "Confidence": 96.52117156982422}, {"Name": "Impala", "Confidence": 96.52117156982422}, {"Name": "Mammal", "Confidence": 96.52117156982422}, {"Name": "Wildlife", "Confidence": 96.52117156982422}, {"Name": "Deer", "Confidence": 91.72703552246094}]"}
    #ops include [ 'PutItem', 'UpdateItem', 'DeleteItem', 'BatchWriteItem', 'PutObject', 'DeleteObject', 'PostObject', 'Publish', 'Invoke' ]
    pl = pl.strip('"}')

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
        retn['op'] = 'DynamoDB=PutItem:{}'.format(current_region)
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
        retn['op'] = 'DynamoDB=UpdateItem'
        print('processPayload<unsupported op>',pl)
        sys.exit(1)

    elif pl.startswith('DeleteItem:'):
        retn['op'] = 'DynamoDB=DeleteItem'
        print('processPayload<unsupported op>',pl)
        sys.exit(1)

    elif pl.startswith('BatchWriteItem:'):
        retn['op'] = 'DynamoDB=BatchWriteItem'
        print('processPayload<unsupported op>',pl)
        sys.exit(1)

    elif pl.startswith('PutObject:'):
        retn['op'] = 'S3=PutObject'
        toks = pl.split(':')
        retn['reg'] = toks[1] #region of both
        retn['tname'] = toks[3]  #Bucket
        retn['kn'] = toks[5]  #fname

    elif pl.startswith('DeleteObject:'):
        retn['op'] = 'S3=DeleteObject'
        toks = pl.split(':')
        retn['reg'] = toks[1] #region of both
        retn['tname'] = toks[3]  #Bucket
        retn['kn'] = toks[5]  #fname

    elif pl.startswith('PostObject:'):
        retn['op'] = 'S3=PostObject'
        toks = pl.split(':')
        retn['reg'] = toks[1] #region of both
        retn['tname'] = toks[3]  #Bucket
        retn['kn'] = toks[5]  #fname

    elif pl.startswith('Publish:'):
        #Publish:us-west-2:TopicArn:arn:aws:sns:us-west-2:443592014519:topicB:Subject:sub1:Message:fname:testfile.txt:prefix:prefB:bkt:cjk-fninvtrigger-b:xxx
        retn['op'] = 'SNS=Publish'
        toks = pl.split(':')
        retn['reg'] = toks[6] #region of topic
        retn['tname'] = toks[8] #topic
        retn['kn'] = toks[10] #subject
        idx = pl.find(':Message:')
        if idx != -1:
            retn['rest'] = pl[idx+9:] #message

    elif pl.startswith('Invoke:'):
        #Invoke:us-west-2:FunctionName:arn:aws:lambda:us-west-2:XXX:function:emptyB:InvocationType:Event
        retn['op'] = 'Invoke:{}'.format(current_region)
        toks = pl.split(':')
        retn['reg'] = toks[1] #region of both
        if len(toks) == 12:
            retn['tname'] = toks[9]  #callee name
            retn['rest'] = '{}'.format(toks[11]) #invocationType
        elif len(toks) == 6:
            retn['tname'] = toks[3]  #callee name
            retn['rest'] = '{}'.format(toks[5]) #invocationType
        else:
            print('processPayload<unsupported Invoke op>',pl)
            assert False
        retn['kn'] = 'unknown'  #callee reqID
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
    
##################### setupParReqs  #######################
def setupParReqs(fname, flist, XRAY_PAR_REQ):
    #get the json from the files
    if os.path.isfile(fname):
        flist.append(fname)
    else:
        path = os.path.abspath(fname)
        for file in os.listdir(fname):
            fn = os.path.join(path, file)
            if os.path.isfile(fn) and fn.endswith('.xray'):
                flist.append(fn)

    #loop through segments to fill in XRAY_PAR_REQ first (with AWS::Lambda segments)
    for fname in flist:
        if DEBUG:
            print('processing xray file {}'.format(fname))
        with open(fname,'r') as f:
            json_dict = json.load(f)

        #timings startup = AL:Dwell+AL:Attempt+ALFN:Initialization(if any)
        #timings execution = ALFN duration
        #timings for sdks are in subsegments under ALFN
        traces = json_dict['Traces']
        for trace in traces:
            segs = trace['Segments']
            for seg in segs:
                xray_str = None
                trid=myid=tname=op=reg=key=keyname=parent_reqID='unknown'
                doc_dict = json.loads(seg['Document'])
                if 'origin' in doc_dict: #AWS::Lambda (parent of Dwell,Attempts)
                    name = doc_dict['name']
                    subid = doc_dict['id']
                    keyname = doc_dict['trace_id']
                    origin = doc_dict['origin']
                    aws = doc_dict['aws']

                    if origin == 'AWS::Lambda': #AWS::Lambda (parent of Dwell,Attempts)
                        if 'resource_arn' not in doc_dict:
                            continue #repeat instance of Lambda SDK call
                        myarn = doc_dict['resource_arn']
                        toks = myarn.split(':') #arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyB
                        reg = toks[3] #region
                        name = toks[6] #function name
                        key = toks[4] #account number
                        #step through subsegments (Dwell and Attempt)
                        subs = doc_dict['subsegments']
                        assert len(subs) <= 2
                        #record time spent in startup
                        parent_reqID = tname = aws['request_id']
                        parent_id = doc_dict['id']
                        dursum = 0.0
                        err = False
                        Done = False
                        for sub in subs:
                            myid = sub['id']
                            start = float(sub['start_time'])
                            end = float(sub['end_time'])
                            dursum += (end-start)
                            status = 200
                            if 'http' in sub and 'response' in sub['http'] and 'status' in sub['http']['response']:
                                status = sub['http']['response']['status']
                                #only Attempts will have a status 
                                if status == 200 or status == 202:
                                    XRAY_PAR_REQ[myid] = parent_reqID
                                    Done = True
                            if status != 200:
                                err = True
                        #record tuple using dwell's ssid
                        ################startup_sum, True if Init, fn_duration
                        if Done:
                            XRAY_REQS[parent_reqID] = (dursum,False,0.0)
                        xray_str = '{}:AWS_Lambda:{}:{}:{}:{}:{}:{}'.format(name,reg,tname,keyname,key,dursum,err)
                        if DEBUG:
                            print('xray {} parent {} payload {}'.format(subid,parent_id,xray_str))

##################### processHybrid  #######################
def processHybrid(fname):
    flist = []
    XRAY_PAR_REQ = {}

    #process filenames and loop through segments to fill in XRAY_PAR_REQ first (with AWS::Lambda segments)
    setupParReqs(fname, flist, XRAY_PAR_REQ)

    #now loop thrugh again and capture the rest (AWS::Lambda::Function's and SDK subsegments)
    for fname in flist:
        with open(fname,'r') as f:
            json_dict = json.load(f)

        #timings startup = AL:Dwell+AL:Attempt+ALFN:Initialization(if any)
        #timings execution = ALFN duration
        #timings for sdks are in subsegments under ALFN
        traces = json_dict['Traces']
        for trace in traces:
            segs = trace['Segments']
            for seg in segs:
                xray_str = None
                trid=myid=tname=op=reg=key=keyname=parent_reqID='unknown'
                doc_dict = json.loads(seg['Document'])
                if 'origin' in doc_dict: #AWS::Lambda (parent of Dwell,Attempts)
                    name = doc_dict['name']
                    subid = doc_dict['id']
                    keyname = doc_dict['trace_id']
                    origin = doc_dict['origin']
                    aws = doc_dict['aws']

                    if origin == 'AWS::Lambda::Function': #AWS::Lambda:Function (parent of Initialization,requests, and SDKs)
                        parent_id = doc_dict['parent_id'] #ID of Attempt event that spawned this FN
                        if parent_id not in XRAY_PAR_REQ:
                            print('ERROR: {} not in {}'.format(parent_id,XRAY_PAR_REQ))
                            assert False
                        reqID = XRAY_PAR_REQ[parent_id] #reqID of the parent of Attempt (FN's reqID)

                        #update tuple
                        tpl = XRAY_REQS[reqID]  #(0:startup_sum, 1:True if Init, 2:fn_duration)
                        assert tpl[2] == 0.0
                        start = float(doc_dict['start_time'])
                        end = float(doc_dict['end_time'])
                        dursum = end-start
                        err = False
                        newtpl = (tpl[0],tpl[1],dursum)
                        XRAY_REQS[reqID] = newtpl  #(0:startup_sum, 1:True if Init, 2:fn_duration)
                        myarn = aws['function_arn']
                        toks = myarn.split(':') #arn:aws:lambda:us-west-2:XXX:function:FnInvokerPyB
                        name = toks[6]
                        reg = toks[3]
                        #tname,key unused
                        xray_str = '{}:AWS_Lambda_FN:{}:{}:{}:unknown:{}:{}'.format(name,reqID,reg,tname,keyname,key,dursum,err)
                        if DEBUG:
                            print('xray {} parent {} payload {}'.format(subid,parent_id,xray_str))

                        #step through subsegments (requests, sdks) 
                        parent_reqID = reqID #reqID of parent to the subsegments that follow
                        parent_id = subid #id of parent to the subsegments that follow
                        subs = doc_dict['subsegments']
                        for sub in subs:
                            #record time spent in requests+sdks
                            name = sub['name']
                            start = float(sub['start_time'])
                            end = float(sub['end_time'])
                            duration = (end-start)
                            if name == 'Initialization':
                                #container was started for this function, add it to the startup overhead and set flag
                                tpl = XRAY_REQS[reqID]
                                newtpl = (tpl[0]+duration,True,tpl[2])
                                XRAY_REQS[reqID] = newtpl  #(0:startup_sum, 1:True if Init, 2:fn_duration)
                                continue
                        
                            #process sdk or requests event
                            xray_str = None
                            trid=myid=tname=op=reg=key=keyname='unknown'
                            err = 'False'
                            myid = sub['id']
                            if 'error' in sub:
                                err = str(sub['error'])
                            if 'aws' in sub:
                                aws = sub['aws']
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
                                if 'http' in sub and 'response' in sub['http']:
                                    keyname = sub['http']['response']['status']
                                skip = False
                                if 'gr_payload' in aws:
                                    pl = aws['gr_payload']
                                    idx = pl.find(':Item:{')
                                    if idx != -1: #DDB 
                                        idx2 = pl.find(':',idx+7)
                                        keyname = pl[idx+7:idx2].strip('"\' ') #DDB keyname
                                        idx = pl.find(',',idx2+1)
                                        key = pl[idx2+1:idx].strip('"\' ') #DDB key
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


                                if not skip:
                                    #length 9 = sdk subsegment
                                    xray_str = '{}:{}:{}:{}:{}:{}:{}:{}:{}'.format(name,op,reg,tname,keyname,key,duration,err,reqID)
                            else:
                                if name == 'requests':
                                    assert 'http' in sub
                                    http = sub['http']
                                    url = http['request']['url'][7:] #trim off the http:// chars
                                    op = http['request']['method']
                                    status = http['response']['status']
                                    #API Gateway url: https://6w1s7kyypi.execute-api.us-west-2.amazonaws.com/beta
                                    if 'amazonaws.com' in url:
                                        toks = url.split('.')
                                        assert toks[3] == 'amazonaws'
                                        reg = toks[2]
                                    
                                    #length 9 = requests subsegment
                                    xray_str = '{}:{}:{}:{}:{}:{}:{}:{}:{}'.format(name,op,reg,tname,url,status,duration,err,parent_reqID)
                                elif 'Dwell Time' not in name and 'Attempt' not in name: #These are already in encapsulated in AWS::Lambda time
                                    #length 5 other subsegment
                                    xray_str = '{}:{}:{}:{}:{}'.format(name,parent_id,duration,err,parent_reqID)

                            if xray_str: #valid if we set it above
                                if DEBUG:
                                    print('xray {} parent {} payload {}'.format(myid,parent_id,xray_str))
                                assert myid not in SUBSEGS_XRAY
                                SUBSEGS_XRAY[myid] = xray_str

                    else:
                        pass #skip all others as they are repeats of SDKs and requests

    if DEBUG:
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
                print('STREAM ENTRY: ',pl_str)
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
                if DEBUG:
                    print('SDK dict: {} {}'.format(reqID, rest_dict))

                #make a child object-- all are possible event sources at this point (B config)
                child = {TYPE:'sdkT',REQ:reqID,SSID:myid,PAYLOAD:rest_dict,TS:start_ts,DUR:0.0,SEQ:seqID,CHILDREN:[]}
                seqID += 1
                calleeReq = 'none'
                if myid in SUBSEGS_XRAY:
                    xray_data = SUBSEGS_XRAY[myid]
                    toks = xray_data.split(':') #length 8 for sdk: #name,op,reg,tname,keyname,key,duration,err
                    assert len(toks) == 9
                    if toks[1] == 'Invoke':
                        child[PAYLOAD]['kn'] = toks[3]
                    child[DUR] = float(toks[6])
                    rest = ''
                    if 'rest' in child[PAYLOAD]: 
                        rest = child[PAYLOAD]['rest']
                    child[PAYLOAD]['rest'] = '{}:error:{}'.format(rest,toks[7])
                else:
                    print('WARNING: {} not found in SUBSEGS_XRAY'.format(myid))
                    print('\tUnable to update duration for SDK\n\t{}'.format(child))
                    child[PAYLOAD]['rest'] = '{}:NOXRAYDATA'.format(rest)

                _,match,_ = getName(child)
                TRIGGERS[match].append(child)
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
                startup = 0.0
                init = False
                duration = 0.0

                assert reqID not in REQS
                trigger,payload = processEventSource(pl)
                if DEBUG:
                    print('entry: {} {} {}'.format(reqID,trigger,payload))

                if reqID in XRAY_REQS:
                    tpl = XRAY_REQS[reqID]  #(0:startup_sum, 1:True if Init, 2:fn_duration)
                    startup = tpl[0]
                    init = tpl[1]
                    duration = tpl[2]
                else:
                    #function triggered by an event not captured by XRay or not sampled by XRay
                    print('WARNING: {} not found in XRAY_REQS\n\t{} {}'.format(reqID,trigger,payload))
                    payload['rest'] = '{}:NOXRAYDATA'.format(payload['rest'])

                ele = {TYPE:'fn',REQ:reqID,SSID:'none',PAYLOAD:payload,TS:ts,DUR:duration,START:startup,SEQ:seqID,CHILDREN:[]}
                seqID += 1
                if trigger: #this lambda was triggered by an event source
                    n,match,_ = getName(ele)
                    assert match in TRIGGERS
                    plist = TRIGGERS[match]
                    #grab the most recent sequence ID (ensure its smaller than ours (seqID-1))
                    parent = None
                    maxseqID = -1
                    for p in plist:
                        if p[SEQ] > maxseqID:
                            maxseqID = p[SEQ]
                            parent = p
                    assert maxseqID != -1 and maxseqID < (seqID-1)
                    parent[CHILDREN].append(ele)
                    SUBREQS[reqID] = ele
                else: 
                    REQS[reqID] = ele

##################### main #######################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GammaRay Stream Parser')
    parser.add_argument('fname',action='store',help='filename containing stream data')
    parser.add_argument('hybrid',action='store',help='filename containing xray data')
    parser.add_argument('--include_all_sdks',action='store_true',default=False,help='set if you want to display non-triggering sdk operations in the graph')
    parser.add_argument('--aggregate',action='store_true',default=False,help='set if you want to display the aggregate graph instead of the instance')
    args = parser.parse_args()

    if not os.path.isfile(args.hybrid) and not os.path.isdir(args.hybrid): 
        parser.print_help()
        print('\nError: hybrid argument must be a file or a directory containing files ending in .xray')
        sys.exit(1)

    processHybrid(args.hybrid)
    parseIt(args.fname, args.hybrid)
    makeDot(args.aggregate,args.include_all_sdks)

