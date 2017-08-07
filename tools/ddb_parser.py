import json,time,os,sys,argparse
import ast
from graphviz import Digraph
from pprint import pprint
from enum import Enum

DEBUG = True
Names = Enum('Names','FN S3R S3W DBR DBW SNS GW')
invokes = 0
invoke_calls = 0
################# processAPICall #################
def processAPICall(n,msg):
    global invoke_calls
    #use 2 letter prefix for name entry for easy acces to key eg SN instead of SNS and S3 for reads/writes,
    #the object carries the more specific type in nm
    nm = None
    if n.startswith('GetObject:') or n.startswith('ListObjects:'): 
        nm = Names.S3R
    elif n.startswith('PutObject:'):
        nm =  Names.S3W
    elif n.startswith('PutItem:'):
        nm =  Names.DBW
    elif n.startswith('GetItem:'):
        nm =  Names.DBR
    elif n.startswith('Publish:'):
        nm =  Names.SNS
    elif n.startswith('Invoke:'):
        invoke_calls += 1
        nm =  Names.FN
    else:
        assert False
    ######## process nm #########
    name = None
    if nm == Names.FN:
        idx = msg.find('SW:FunctionName:')
        if idx != -1:
            name = 'FN:{}'.format(msg[idx+16:])
        else:
            print('Error: expected to find FunctionName in msg: {}'.format(msg))
            assert False
    elif nm == Names.S3R:
        idx = msg.find('SW:Bkt:')
        if idx != -1:
            idx2 = msg.find(':Key:')
            if idx2 != -1:
                name = 'S3:{}:{}'.format(msg[idx+7:idx2],msg[idx2+5:])
            else:
                print('Error: expected to find :Key: in msg: {}'.format(msg))
                assert False
        else:
            idx = msg.find('ListObjects:')
            if idx != -1:
                rest = msg[idx+12:]
                rest = ast.literal_eval(rest) #turn it into a dictionary
                name = 'S3:{}:{}'.format(rest['Bucket'],rest['Prefix'])
            else:
                print('Error: expected to find SW:Bkt or :ListObjects: in msg: {}'.format(msg))
                assert False
    elif nm == Names.S3W:
        idx = msg.find('SW:Bkt:')
        if idx != -1:
            idx2 = msg.find(':Key:')
            if idx2 != -1:
                name = 'S3:{}:{}'.format(msg[idx+7:idx2],msg[idx2+5:])
            else:
                print('Error2: expected to find :Key: in msg: {}'.format(msg))
                assert False
        else:
            print('Error2: expected to find SW:Bkt: in msg: {}'.format(msg))
            assert False
    elif nm == Names.DBR:
        idx = msg.find('SW:TableName:')
        if idx != -1:
            idx = msg.find(':Key:')
            if idx != -1:
                name = 'DB:{}:{}'.format(msg[idx+13:idx2],msg[idx2+5:])
            else:
                print('Error3: expected to find Key: in msg: {}'.format(msg))
                assert False
        else:
            print('Error3: expected to find SW:TableName: in msg: {}'.format(msg))
            assert False
    elif nm == Names.DBW:
        idx = msg.find('SW:TableName:')
        if idx != -1:
            idx = msg.find(':Item:')
            if idx != -1:
                name = 'DB:{}:{}'.format(msg[idx+13:idx2],msg[idx2+6:])
            else:
                print('Error4: expected to find Item: in msg: {}'.format(msg))
                assert False
        else:
            print('Error4: expected to find SW:TableName: in msg: {}'.format(msg))
            assert False
    elif nm == Names.SNS:
        idx = msg.find('SW:sns:Publish:Topic:arn:aws:sns:')
        if idx != -1:
            idx = msg.find(':Subject:')
            if idx != -1:
                name = 'SN:{}:{}'.format(msg[idx+33:idx2],msg[idx2+9:])
            else:
                name = 'SN:{}'.format(msg[idx+33:])
        else:
            print('Error5: expected to find SW:sns:Publish:Topic: in msg: {}'.format(msg))
            assert False
    #elif nm == Names.GW:
        #pass
    else:
        assert False
    return nm,name

################# process #################
def process(obj,reqDict,SEQs,KEYs):
    global invokes
    reqblob = obj['requestID']['S'].split(':')
    req = reqblob[0]
    reqStr = reqblob[1]
    if len(reqblob) > 2:
        reqStr += ':{}'.format(reqblob[2])
        assert len(reqblob)<=3

    ts = float(obj['ts']['N'])
    eventOp = obj['eventOp']['S'] #will be set on receipt of an API call
    es = obj['eventSource']['S'] #will be set on receipt of an API call
    msg = obj['message']['S']

    #extract reqID,nm,item,ip
    parent_obj = None
    nm = None
    name = 'unknown'
    ip = 'unknown'
    skipInvoke = False
    duration = 0
    if reqStr == 'exit': 
        duration = obj['duration']
    elif reqStr == 'entry': 
        nm = Names.FN            
        if 'thisFnARN' in obj:
            arn = obj['thisFnARN']['S'].split(':')
            name = 'FN:{}:{}'.format(arn[6],req)
        if 'sourceIP' in obj:
            ip = obj['sourceIP']
        if eventOp.startswith('ObjectCreated:'):
            #link to existing Names.S3W object
            msg = obj['message']['S'].split(':')
            name = 'S3W:{}:{}'.format(msg[0],msg[1])
            assert name in KEYs
            eleTuple = KEYs.pop(name,None)
            source_name = name #for debugging
            assert eleTuple[1] in SEQs
            parent_obj = SEQs[eleTuple[1]]
        elif eventOp.startswith('lib:invokeCLI:'):
            #link to existing Names.FN
            idx = es.find('lib:invokeCLI:') #lib call from another lambda
            invokes += 1
            if idx != -1: 
                tmp1 = es[idx+14:].split(':')
                source_name = 'FN:{}'.format(tmp1[0]) #for debugging
                parent_req = '{}'.format(tmp1[1])
                assert parent_req in reqDict
                parent_obj = reqDict[parent_req]
            else:
                print('Error: expected to find invokeCli in msg: {}'.format(msg))
                assert False
        elif eventOp.startswith('ext:invokeCLI'):
            #invoke from command line (aws tools remotely)
            nm = Names.FN            
        else:
            print('Error: unhandled entry type: {} {}'.format(reqStr,eventOp))
            assert False
    else: #other event, record it to build trace
        print('APICall:',req,reqStr,obj)
        nm ,name = processAPICall(reqStr, msg)
        if nm == Names.S3W or nm == Names.DBW or nm == Names.SNS:
            #possible function trigger (writes only trigger lambdas in S3, DynamoDB, and SNS
            #store them in KEYs but just keep the last one (most recent) as events are in order
            ele = DictEle(obj,req,name,nm,ts)
            seq = ele.getSeqNo()
            assert seq not in SEQs
            SEQs[seq] = ele #keep map by seqNo
            assert req in reqDict
            parent_obj = reqDict['req']
            parent_obj.addChild(ele)
            KEYs[name] = ele #store for later use, overwrite last key (processing in sequence order)

        print('\t',nm,name)
        if nm == Names.FN:
            skipInvoke = True
        else: #get parent object
            #assert req in reqDict #if processing in order, this must be true, skip for now HERE CJK
            if req in reqDict: 
                parent_obj = reqDict[req]

    if not skipInvoke: #skip API calls to invoke as we capture requestID of caller in callee header
        if req in reqDict:
            #a non-entry (other event) or exit
            oldele = reqDict[req]
            if reqStr == 'exit':
                assert parent_obj is None
                old_duration = oldele.getDuration()
                assert old_duration == 0
                oldele.setDuration(duration)
                print('EXIT: Name: {}, NM: {}, IP: {}'.format(name,nm,ip))
            else:
                assert reqStr != 'entry'
                ele = DictEle(obj,req,name,nm,ts)
                oldele.addChild(ele)
                seq = ele.getSeqNo()
                assert seq not in SEQs
                SEQs[seq] = ele #keep map by seqNo
                if name not in KEYs:
                    KEYs[name] = (ele,seq) #keep map by keyname, make seqNo and ts easy to retrieve
                else:
                    assert False # more than one with the same key, get the one earliest in time
            print('EVENT: Name: {}, NM: {}, IP: {}'.format(name,nm,ip))
        else:
            assert reqStr != 'exit'
            ele = DictEle(obj,req,name,nm,ts)
            seq = ele.getSeqNo()
            assert seq not in SEQs
            SEQs[seq] = ele #keep map by seqNo
            reqDict[req] = ele
            if reqStr == 'entry': 
                print('ENTRY: Name: {}, NM: {}, IP: {}'.format(name,nm,ip))
                if parent_obj:
                    parent_obj.addChild(ele)
                    print('\tENTRY: adding parent {}'.format(parent_obj.getName()))
            else:
                if parent_obj is None:
                    #this shouldn't happen if processing in order, handle for now HERE CJK
                    assert name not in KEYs
                    KEYs[name] = (ele,seq)
                else:
                    print('EVENT: Name: {}, NM: {}, IP: {}'.format(name,nm,ip))
                    assert parent_obj is not None
                    parent_obj.addChild(ele)
    
def makeDot(reqDict):
    dot = Digraph(comment='Spot',format='pdf')
    for key in reqDict:
        obj = reqDict[key]
        p = str(obj.getSeqNo())
        p1 = str(obj.getName())
        dot.node(p,p1)
        for lst in obj.children_lists:
            childlist = obj.children_lists[lst]
            for child in childlist:
                c = str(child.getSeqNo())
                c1 = str(child.getName())
                dot.node(c,c1)
                dot.edge(p,c)
        dot.render('spotgraph', view=True)
        return
         
def parseIt(event):
    fname = None
    reqDict = {} #dictionary holding request (DictEle) objects by requestID
    SEQs = {} #dictionary by seqID holding DictEles, for easy traversal by seqNo
    KEYs = {} #dictionary by name (key) for events holding (DictEle,req,seq,ts), popped when assigned by earliest ts
    #check that the file is available 
    fname = None
    if 'fname' in event:
        fname = event['fname']
        if not os.path.exists(fname) or not os.path.isfile(fname):
            fname = None
    if not fname:
        print('Unable to find/open file in parseIt')
        return
    print('processing file: {}'.format(fname))

    data = None
    reqs = []
    count = 0
    if 'oldversion' in event:
        #decode the json file
        with open(fname) as data_file:    
            data = json.load(data_file)
        if not data:
            return
        #put them in sorted order by timestamp
        reqs = sorted(data['Items'], key=lambda k: k['ts'].get('N', 0))
    else:
        with open(fname) as data_file:    
            for line in data_file:
                if line.startswith('SHARD'):
                    continue #skip it
                #get item object xxx:INSERT:yyy:{item}
                if ':INSERT:' in line: #skip the REMOVE entries
                    idx = line.find(':')
                    idx = line.find(':',idx+1)
                    idx = line.find(':',idx+1)
                    rest = ast.literal_eval(line[idx+1:]) #turn it into a dictionary
                    reqs.append(rest)

    count = len(reqs)
    counter = 0
    missed_count = 0
    missing = {}
    for item in reqs:
        counter += 1
        #if counter > 10:
            #break
        if DEBUG:
            print(item)
        process(item,reqDict,SEQs,KEYs)


        '''
        reqblob = item['requestID']['S'].split(':')
        req = reqblob[0]
        reqStr = reqblob[1]
        if len(reqblob) > 2:
            reqStr += ':{}'.format(reqblob[2])
            assert len(reqblob)<=3

        ts = float(item['ts']['N'])
        eventOp = item['eventOp']['S'] #will be set on receipt of an API call

        #nm = getName(reqStr,item)
        if not nm: #process the exit or its an API call like invoke (just count it)
            assert req in reqDict
            if reqStr == 'exit': 
                #update timings only
                ele = reqDict[req]
                #ele.endTime(item['duration'])
            else:
                missed_count += 1
            continue

        if req not in reqDict:
            if reqStr != 'entry': #we haven't see the entry of this one yet... timestamp misalignment perhaps
                missing[req] = reqStr

            ele,parent_req = makeEle(item,req,nm,reqStr)
            if parent_req:
                if parent_req not in reqDict:
                    print('ERROR, found a function with a parent not in dictionary! c{}\n{}'.format(req,item))
                    sys.exit(1)
                pele = reqDict[parent_req]
                pele.addChild(ele,nm)
            reqDict[req] = ele
            obj = ele
        else:
            if reqStr == 'entry': #entry is coming after an entry's event, not good
                ele,parent_req = makeEle(item,req,nm,reqStr)
                if parent_req:
                    if parent_req not in reqDict:
                        print('ERROR, found a function with a parent not in dictionary! c{}\n{}'.format(req,item))
                        sys.exit(1)
                    pele = reqDict[parent_req]
                    pele.addChild(ele,nm)
                reqDict[req] = ele
                obj = ele
                missing.pop(req, None) #remove it from missing
            else:
                assert reqStr != 'exit'
                child,_ = makeEle(item,req,nm,reqStr)
                ele = reqDict[req]
                ele.addChild(child,nm)
                obj = child
        if DEBUG:
            print(reqStr,nm,req,obj.getSeqNo())
        '''

    makeDot(reqDict)
    print("missed_count: {}, objs missing {}".format(missed_count,len(missing)))
    print("invoked_count: {}, invokes {}".format(invoke_calls,invokes))

class DictEle:
    __seqNo = 0

    #def addChild(self,child,childtype):
        #if childtype not in self.__children_lists:
            #self.__children_lists[childtype] = []
        #self.__children_lists[childtype].append(child)
    def addChild(self,child):
        if child not in self.__children:
            self.__children.append(child)
    def setDuration(self,duration):
        self.__duration = duration
    def getDuration(self):
        return self.__duration
    def getBlob(self):
        return self.__ele
    def getName(self):
        return self.__name
    def getSeqNo(self):
        return self.__seq
    def getReqId(self):
        return self.__reqID
    def getNM(self):
        return self.__nm
    def getSourceIP(self):
        if 'sourceIP' in self.__blob:
            return self.__blob['sourceIP']
        else:
            return None

    def __init__(self,blob,reqID,name,nm,ts):
        #self.__children_lists = {} #list of DictEles per Names.enum
        self.__children = []
        self.__seq = self.getAndIncrSeqNo()
        self.__ts = ts
        self.__nm = nm
        self.__name = name
        self.__reqID = reqID
        self.__duration = 0
        self.__ele = blob

    @staticmethod
    def getAndIncrSeqNo(incr=1):
        seqno =  DictEle.__seqNo
        DictEle.__seqNo += incr
        return seqno

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DynamoDB spotFns Table data Parser')
    parser.add_argument('fname',action='store',help='filename to process')
    parser.add_argument('--fname_is_dbdump',action='store_true',default=False,help='file is dbdump file')
    #parser.add_argument('schema',action='store',help='schema of file to process')
    args = parser.parse_args()
    event = {}
    event['fname'] = args.fname
    if args.fname_is_dbdump:
        event['oldversion'] = 'any text will work'
    #event['schema'] = args.schema
    parseIt(event)

