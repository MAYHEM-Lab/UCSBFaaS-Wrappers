import json,time,os,sys,argparse,statistics,ast
from pprint import pprint
from graphviz import Digraph
from enum import Enum

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
TRIGGERS = {}
SDKS = []
REPEATS = []
eleID = 1
seqID = 1
NODES = {}
##################### getName #######################
def getName(req):
    pl = req[PAYLOAD]
    name = ''
    if DEBUG:
        print('payload: ',pl)

    if type(pl) == dict:
        #dynamic SDK entry 
        name = pl['name']
        rest = ""
        if name == 'requests':
            #HTTP operation
            http = pl['http']
            reqst = http['request']
            url = reqst['url']
            if url.startswith('http://'):
                url = url[7:]
            name = 'HTTP={} {}'.format(reqst['method'],url)
            rest = '{}'.format(http['response']['status'])
        else:
            aws = pl['aws']
            name += ' {}'.format(aws['operation'])
            if aws['operation'] == 'PutItem':
                tname,reg,keyname,key = getDetails(aws)
                name = 'DDB=PutItem {}\n{} {}={}'.format(tname,reg,keyname,key)
            elif aws['operation'] == 'GetItem':
                tname,reg,keyname,key = getDetails(aws)
                name = 'NONTRIGGER:DDB=GetItem {}\n{} {}={}'.format(tname,reg,keyname,key)
            else:
                name = 'NONTRIGGER:{}'.format(name)
            
        return rest,name

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
            name += ' {}'.format(pl[idx+10:idx2]) #add the region
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
        name = 'FN={} {}'.format(name,pl[idx+11:idx2])
        
    else:
        assert True #shouldn't be here

    return "",name

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
    details = ''
    assert pl.find(':es:') != 1
    event_source = pl
    if ':ddb:' in event_source:
        #ddb:arn:aws:dynamodb:us-west-2:443592014519:table/image-proc-S/stream/2017-09-20T20:26:50.795:keys:id:op:INSERT
	#get tablename
        assert pl.find('esARN:') != -1
        idx = event_source.find(':table/')
        idx2 = event_source.find('/',idx+7)
        tname = event_source[idx+7:idx2]
        #get the region
        idx = event_source.find('arn:aws:dynamodb:')
        idx2 = event_source.find(':',idx+17)
        region = event_source[idx+17:idx2]

        idx = event_source.find(':keys:')
        idx2 = event_source.find(':',idx+6)
        keyname = event_source[idx+6:idx2]

        idx3 = event_source.find(':op',idx2+1)
        key_str = event_source[idx2+1:idx3]
        #key_str is {'S': 'imgProc/d1.jpgbc37'}
        toks = key_str.split(' ')
        key = toks[1].strip("}'")

        details = '{}:{}:{}:{}'.format(tname,region,keyname,key)
    return details

##################### processChild #######################
def getDetails(payload):
    reg = payload['region']
    gr_pl = payload['gr_payload'] #string
    #'payload:TableName:image-proc-D:Item:{"id": "imgProc/d1.jpg639b", "labels": "[{"Name": "Animal", "Confidence": 96.52118682861328}, {"Name": "Gazelle", "Confidence": 96.52118682861328}, {"Name": "Impala", "Confidence": 96.52118682861328}, {"Name": "Mammal", "Confidence": 96.52118682861328}, {"Name": "Wildlife", "Confidence": 96.52118682861328}, {"Name": "Deer", "Confidence": 91.72703552246094}]"}'
    idx = gr_pl.find(':TableName:')
    idx2 = gr_pl.find(':Item:{')
    if idx2 == -1 and idx != -1:
        idx2 = gr_pl.find(':Key:{')
        
    assert idx != -1 and idx2 != -1
    tname = gr_pl[idx+11:idx2]
    idx3 = gr_pl.find(':',idx2+7) #should still work for Item or Key because of extra quote that will be stripped off below for Item
    keyname = gr_pl[idx2+7:idx3].strip("\"'\\")
    idx2 = gr_pl.find(',',idx3+2)
    key = gr_pl[idx3+2:idx2].strip("\"'\\")
    return tname,reg,keyname,key

##################### processChild #######################
def processChild(child_dict):
    details = ''
    #if child is a possible event source, it can also be a parent
    #{TYPE:'fn,sdk,sdkT',REQ:reqID,PAYLOAD:pl,TS:ts,DUR:dur,CHILDREN:[]}
    payload = child_dict[PAYLOAD]
    if 'aws' in payload: #dynamic (B or D config)
        payload = payload['aws']
        if 'operation' in payload and payload['operation'] == 'PutItem':
            tname,reg,keyname,key = getDetails(payload)
            details = '{}:{}:{}:{}'.format(tname,reg,keyname,key)
            return details
        # potential trigger: sdkend: (a1fc649f-a626-11e7-a9db-bdd2537308bd SDKend:{"type": "subsegment", "id": "3ffa848423654d79", "trace_id": "1-59d00d0b-f18722cf531ce1db265e3814", "parent_id": "145c43af5f4c6069", "start_time": 1506807055.0124357, "end_time": 1506807055.2713935, "name": "requests", "namespace": "remote", "http": {"request": {"method": "POST", "url": "http://httpbin.org/post"}, "response": {"status": 200}}, "error": false} 1506807055272.0)

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
        #rewrite name to strip off any excess characters 
        #keyname = item[0].strip('\'\\ ,:').replace('/','_|_')
        #key = item[1].strip('\'\\ ,').replace('/','_|_')
        keyname = item[0].strip('\'\\ ,:')
        key = item[1].strip('\'\\ ,')
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
def processRecord(reqID,pl,ts,dynamic=False,fxray=None):
    global seqID
    #if pl.startswith('pl:arn:aws:lambda'):
    if pl.startswith('pl:'):
        #entry
        if not fxray:  #configuration B has no exits
            SDKS.append((reqID,pl,ts))
            print('pushedent {}'.format((reqID,pl,ts)))
        assert reqID not in REQS
        ele = {TYPE:'fn',REQ:reqID,PAYLOAD:pl,TS:ts,DUR:0.0,SEQ:seqID,CHILDREN:[]}
        seqID += 1

        retn = processEventSource(pl)
        if retn != '': #this lambda was triggered by an event source
            assert retn in TRIGGERS
            parent = TRIGGERS[retn]
            parent[CHILDREN].append(ele)
            SUBREQS[reqID] = ele
        else: 
            REQS[reqID] = ele
        return
    if pl == 'end': #will only occur for S and D
        assert not fxray  #configuration B has no SDKstarts
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
        assert not fxray  #configuration B has no SDKstarts
        if pl in REPEATS:
            if DEBUG:
                print('payload already in repeats')
            return
        SDKS.append((reqID,pl,ts))
        print('pushed {}'.format((reqID,pl,ts)))
        REPEATS.append(pl)
        return

    if pl.startswith('SDKend'):
        if pl in REPEATS:
            if DEBUG:
                print('sdkend payload already in repeats')
            return
        REPEATS.append(pl)
        mystr = pl[7:].strip()
        pldict = json.loads(mystr)
        if dynamic:
            start_pl = pldict
        t = pldict['type']
        myid = pldict['id']
        pid = pldict['parent_id']
        trid = pldict['trace_id']
        if fxray:  #configuration B has no SDKstarts
            #update the SDKs duration
            start_ts = float(pldict['start_time'])*1000
            ts = float(pldict['end_time'])*1000
            dur = ts-start_ts
        else:
            laststart = SDKS.pop()
            print('popped {}'.format(laststart))
            assert not laststart[1].startswith('pl:') #make sure that its an SDKstart
            assert laststart[0] == reqID  #true of we hit an end without a start
            #tmpstr = pl[7:]
            #if "\\\\" in tmpstr:
                #tmpstr = tmpstr.replace("\\\\","\\")
            #if "\\'" in tmpstr:
                #tmpstr = tmpstr.replace("\\'",'\\"')
    
            #update the SDKs duration
            start_pl = laststart[1]
            start_ts = laststart[2]
            dur = ts-start_ts
    
            mystr = laststart[1].strip("'")[9:]
            pldict = json.loads(mystr)
            t2 = pldict['type']
            myid2 = pldict['id']
            pid2 = pldict['parent_id']
            assert pid == pid2 and t == t2 and myid == myid2
    
        #make a child object
        child = {TYPE:'sdk',REQ:reqID,PAYLOAD:start_pl,TS:start_ts,DUR:dur,SEQ:seqID,CHILDREN:[]}
        seqID += 1
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

##################### processHybrid  #######################
def processHybrid(fname):
    flist = []
    #get the json from the files
    if os.path.isfile(fname):
        flist.append(fname)
    else:
        for file in os.listdir(fname):
            fn = os.path.join(path, file)
            if os.path.isfile(fn) and fn.endswith('.xray'):
                flist.append(fn)

    for fname in flist:
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
                print()
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
                    if origin == 'AWS::Lambda':
                        print(doc_dict)
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
                                        keyname = pl[idx+7:idx2].strip('"\' ')
                                        idx = pl.find(',',idx2+1)
                                        key = pl[idx2+1:idx].strip('"\' ')
                                    elif idx3 != -1:
                                        #payload:arn:aws:lambda:us-west-2:443592014519:function:FnInvokerPyB:FunctionName:arn:aws:lambda:us-west-2:443592014519:function:DBModPyB:InvocationType:Event:Payload
                                        idx = pl.find(':',idx3+29)
                                        reg = pl[idx3+29:idx]
                                        idx = pl.find(':function:')
                                        idx2 = pl.find(':',idx+10)
                                        tname = pl[idx+10:idx2]
                                        idx = pl.find(':InvocationType:')
                                        idx2 = pl.find(':',idx+16)
                                        keyname= pl[idx+15:idx2] #Event (Async) or RequestResponse (Sync)
                                    
                                print(doc_dict)
                                print('\t{} {}:{}:{}:{}:{}:{}:{}:{}'.format(subid,name,op,reg,tname,keyname,key,subs['start_time'],subs['end_time']))
                                if trid != 'unknown':
                                    print('\ttrid: {}'.format(trid))
    
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
                    #print('{} other: {}:{}:{}'.format(myid,name,doc_dict['start_time'],doc_dict['end_time']))
                    
    print('DONE')
            
   

##################### parseItS #######################
def parseItS(fname):
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
            if '"SDKstart:' in line or "'SDKstart:" in line:
                startidx = line.find('SDKstart')
                idx = line.find("}, 'reqID': {'S': '")
                tsidx = line.find("ts': {'N': '")
                pl_str = line[startidx:idx]
                reqID_str = line[idx+19:tsidx]
                ts_str = line[tsidx+12:]
            elif "'payload': {'S': 'end'}" in line: 
                #14274300000000014501584606 INSERT:c6665f0157efc534b3ef6dc125ee90e6:{'payload': {'S': 'end'}, 'reqID': {'S': 'b4c12454-a615-11e7-9718-ef4e8bed8d19:exit900fadaa'}, 'ts': {'N': '1506799790528'}}
                toks = line.split(' ')
                pl_str = toks[3]
                reqID_str = toks[6]
                ts_str = toks[9]
            else:
                #14274400000000014501587215 INSERT:13090a2cba01993346e06e6905b1e110:{'payload': {'S': "pl:arn:aws:lambda:us-west-2:443592014519:function:DBSyncPySesARN:arn:aws:dynamodb:us-west-2:443592014519:table/image-proc-S/stream/2017-09-20T20:26:50.795:es:ddb:keys:id:{'S': 'imgProc/d1.jpgbc37'}:op:INSERT"}, 'reqID': {'S': '6f7372f9-16a5-4251-930f-b13245edb3a0:entryce471e79'}, 'ts': {'N': '1506799794827'}}
                idx = line.find("'payload': {'S': ")
                idx2 = line.find(", 'reqID': {")
                assert idx2 > idx
                pl_str = line[idx+17:idx2]
                rest = line[idx2+12:]
                toks = rest.split(' ')
                reqID_str = toks[1]
                ts_str = toks[4]
            pl = pl_str.strip("'\",}{ ")
            ts = float(ts_str.strip("'\",}{ "))
            reqID = reqID_str.strip("'\",}{ ")
            idx = reqID.find(':')
            reqID = reqID[:idx]
            if DEBUG:
                print('\ncalling processRecord on\nPL={}\nREQID={}\nTS={}'.format(pl,reqID,ts))
            processRecord(reqID,pl,ts)

##################### parseItD #######################
def parseItD(fname,fxray=None):
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
            if DEBUG:
                print('\nprocessing {}'.format(line))

            idx = line.find("'payload': {'S': '{")
            if idx != -1:
                idx3 = line.find('"in_progress": true}')
                idx2 = line.find("}, 'reqID': {")
                assert idx2 > idx
                if idx3 != -1:
                    #subsegment start or middle
                    pl_str = 'SDKstart:{}'.format(line[idx+18:idx2])
                else:
                    pl_str = 'SDKend:{}'.format(line[idx+18:idx2])
                    #subsegment end
                rest = line[idx2+13:]
                toks = rest.split(' ')
                reqID_str = toks[1]
                ts_str = toks[4]
            else:
                idx = line.find("'payload': {'S': 'pl:")
                idx2 = line.find("'payload': {'S': \"pl:")
                if idx != -1 or idx2 != -1:
                    if idx == -1:
                        idx = idx2
                    #entry
                    idx3 = line.find(", 'reqID': {'S': ")
                    idx4 = line.find(", 'ts': {'N': ")
                    pl_str = line[idx+18:idx3-2] #subtract off quote and curly brace
                    reqID_str = line[idx3+17:idx4]
                    ts_str = line[idx4+13:]
                else: 
                    idx = line.find("'payload': {'S': 'end'")
                    assert idx != -1
                    #exit
                    pl_str = 'end'
                    toks = line.split(' ')
                    reqID_str = toks[6]
                    ts_str = toks[9]
                
            pl = pl_str.strip("'\", ")
            if "\\\\" in pl:
                pl = pl.replace("\\\\","\\")
            if "\\'" in pl:
                pl = pl.replace("\\'",'\\"')
            ts = float(ts_str.strip("'\",}{ "))
            reqID = reqID_str.strip("'\",}{ ")
            idx = reqID.find(':')
            reqID = reqID[:idx]
            if DEBUG:
                print('calling processRecord on\nPL={}\nREQID={}\nTS={}'.format(pl,reqID,ts))
            processRecord(reqID,pl,ts,True,fxray)

 
##################### main #######################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Stream Dump Parser')
    parser.add_argument('fname',action='store',help='filename containing data')
    parser.add_argument('--dbdump',action='store_true',default=False,help='file is in json dynamodump format')
    parser.add_argument('--dynamic',action='store_true',default=False,help='file is in json streamD format')
    parser.add_argument('--static',action='store_true',default=False,help='file is in json streamS format')
    parser.add_argument('--hybrid',action='store',default=None,help='directory or file containing output from xray get_batch_traces -- file names must end in .xray')
    args = parser.parse_args()

    if not args.dbdump and not args.dynamic and not args.static and not args.hybrid:
        parser.print_help()
        print('\nError: must choose one of the four file types')
        sys.exit(1)

    if args.dbdump:
        parser.print_help()
        print('\nError: dbdump and dynamic not supported yet')
        sys.exit(1)

    if args.hybrid:
        if not os.path.isfile(args.hybrid) and not os.path.isdir(args.hybrid): 
            parser.print_help()
            print('\nError: hybrid argument must be a file or a directory containing files ending in .xray')
            sys.exit(1)

        processHybrid(args.hybrid)
        parseItD(args.fname, args.hybrid)
        if DEBUG:
            for ele in SDKS:
                print('SDK: ',ele)
        assert SDKS == []
        makeDotAggregate()

    elif args.dynamic:
        parseItD(args.fname)
        if DEBUG:
            for ele in SDKS:
                print('SDK: ',ele)
        assert SDKS == []
        makeDotAggregate()

    elif args.static:
        parseItS(args.fname)
        assert SDKS == []
        makeDotAggregate()
        

#hybrid
#origin AWS:Lambda (LAMBDA) has same trace_id as AWS:Lambda:function (function_arn) in invocation
#AWS:Lambda entry holds the requestID to which db entries are linked
#all others are linked via subsegments
