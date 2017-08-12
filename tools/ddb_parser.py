import json,time,os,sys,argparse
import ast
from graphviz import Digraph
from pprint import pprint
from enum import Enum

DEBUG = False
Names = Enum('Names','FN S3R S3W DBR DBW SNS GW')
Color = Enum('Color','WHITE GRAY BLACK')
invokes = 0
invoke_calls = 0
max_seq_no = 0
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
                name = 'S3R:{}:{}'.format(msg[idx+7:idx2],msg[idx2+5:])
            else:
                print('Error: expected to find :Key: in msg: {}'.format(msg))
                assert False
        else:
            idx = msg.find('ListObjects:')
            if idx != -1:
                rest = msg[idx+12:]
                rest = ast.literal_eval(rest) #turn it into a dictionary
                name = 'S3R:{}:{}'.format(rest['Bucket'],rest['Prefix'])
            else:
                print('Error: expected to find SW:Bkt or :ListObjects: in msg: {}'.format(msg))
                assert False
    elif nm == Names.S3W:
        idx = msg.find('SW:Bkt:')
        if idx != -1:
            idx2 = msg.find(':Key:')
            if idx2 != -1:
                name = 'S3W:{}:{}'.format(msg[idx+7:idx2],msg[idx2+5:])
            else:
                print('Error2: expected to find :Key: in msg: {}'.format(msg))
                assert False
        else:
            print('Error2: expected to find SW:Bkt: in msg: {}'.format(msg))
            assert False
    elif nm == Names.DBR:
        idx = msg.find('SW:TableName:')
        if idx != -1:
            idx2 = msg.find(':Key:')
            if idx2 != -1:
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
            idx2 = msg.find(':Item:')
            if idx2 != -1:
                name = 'DB:{}:{}'.format(msg[idx+13:idx2],msg[idx2+6:])
            else:
                print('Error4: expected to find Item: in msg: {}'.format(msg))
                assert False
        else:
            print('Error4: expected to find SW:TableName: in msg: {}'.format(msg))
            assert False
    elif nm == Names.SNS:
        #idx = msg.find('SW:sns:Publish:Topic:arn:aws:sns:')
        idx = msg.find('SWsns:Publish:Topic:arn:aws:sns:')
        #TODO fix this
        if idx != -1:
            idx2 = msg.find(':Subject:')
            if idx2 != -1:
                name = 'SN:{}:{}'.format(msg[idx+32:idx2],msg[idx2+9:])
            else:
                name = 'SN:{}'.format(msg[idx+32:])
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
    if 'requestID' not in obj:
        return
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
        duration = obj['duration']['N']
        assert req in reqDict
        parent_obj = reqDict[req]
        assert parent_obj.getDuration() == 0
        parent_obj.setDuration(duration)
        #check for error and note it
        err = obj['error']['S']
        if 'SpotWrap_exception' in err:
            parent_obj.setErr(err)
        if DEBUG: 
            print('EXIT: Name: {}, NM: {}, IP: {}'.format(parent_obj.getName(),parent_obj.getNM(),parent_obj.getSourceIP()))
    elif reqStr == 'entry':  ############ function entry ##################
        nm = Names.FN            
        if 'thisFnARN' in obj:
            arn = obj['thisFnARN']['S'].split(':')
            name = 'FN:{}:{}'.format(arn[6],req)
        if 'sourceIP' in obj:
            ip = obj['sourceIP']
        ele = DictEle(obj,req,name,nm,ts)
        seq = ele.getSeqNo()
        assert seq not in SEQs
        SEQs[seq] = ele #keep map by seqNo
        #only insert it into reqDict if it doesn't have a parent!
        reqDict[req] = ele
        if DEBUG:
            print('ENTRY: Name: {}, NM: {}, IP: {}'.format(ele.getName(),ele.getNM(),ele.getSourceIP()))
        if eventOp.startswith('ObjectCreated:'):
            #link to existing Names.S3W object
            msg = obj['message']['S'].split(':')
            name = 'S3W:{}:{}'.format(msg[0],msg[1])
            assert name in KEYs
            eleList = KEYs[name]
            parent_obj = None
            for tempele in eleList:
                if not parent_obj:
                    parent_obj = tempele
                else:
                    if tempele.getSeqNo() < parent_obj.getSeqNo():
                        #tempele occured earlier than parent_obj, so use tempele instead
                        parent_obj = tempele
            assert parent_obj is not None
            eleList.remove(parent_obj)
            source_name = name #for debugging
            if DEBUG:
                print('\tAdding child name: {}, to name {}'.format(ele.getName(),parent_obj.getName()))
            parent_obj.addChild(ele)
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
                parent_obj.addChild(ele)
                if DEBUG:
                    print('\tAdding child name: {}, to name {}'.format(ele.getName(),parent_obj.getName()))
            else:
                print('Error: expected to find invokeCli in msg: {}'.format(msg))
                assert False
        elif eventOp.startswith('ext:invokeCLI') or es.find('ext:invokeCLI') != -1:
            #invoke from command line (aws tools remotely), there is no parent
            pass
        elif eventOp.startswith('Notification'):
            #invoke from SNS notification
            arn = es.split(':') #arn
            idx = msg.find(':') #subject:rest
            subject = msg[0:idx]
            message = msg[idx+1:]
            #SN:region:acct:topic:subject:Message:msg
            name = 'SN:{}:{}:{}:{}:Message:{}'.format(arn[3],arn[4],arn[5],subject,message)
            assert name in KEYs
            eleList = KEYs[name]
            parent_obj = None
            for tempele in eleList:
                if not parent_obj:
                    parent_obj = tempele
                else:
                    if tempele.getSeqNo() < parent_obj.getSeqNo():
                        #tempele occured earlier than parent_obj, so use tempele instead
                        parent_obj = tempele
            assert parent_obj is not None
            eleList.remove(parent_obj)
            source_name = name #for debugging
            if DEBUG:
                print('\tAdding child name: {}, to name {}'.format(ele.getName(),parent_obj.getName()))
            parent_obj.addChild(ele)
        else:
            print('WARNING: function has no parent! {} {}'.format(reqStr,eventOp))
            #assert False
    else: #other event, record it to build trace
        nm ,name = processAPICall(reqStr, msg)
        assert req in reqDict
        parent_obj = reqDict[req]
        if nm == Names.S3W or nm == Names.DBW or nm == Names.SNS:
            if DEBUG:
                print('\tAPICall:',req,reqStr,nm,name)
            #possible function trigger (writes only trigger lambdas in S3, DynamoDB, and SNS
            #store them in KEYs even if they are duplicate
            #if processed from the stream
            ele = DictEle(obj,req,name,nm,ts)
            seq = ele.getSeqNo()
            assert seq not in SEQs
            SEQs[seq] = ele #keep map by seqNo
            parent_obj.addChild(ele)
            if DEBUG:
                print('\tAdding child name: {}, to name {}'.format(ele.getName(),parent_obj.getName()))
            KEYs.setdefault(name,[]).append(ele) #store duplicates if any

        if nm == Names.FN:
            skipInvoke = True
    
def dotGen(dot,obj,reqDict,KEYs):
    global max_seq_no
    eleSeqNo = obj.getSeqNo()
    eleID = str(eleSeqNo)
    eleName = '{}:{}'.format(obj.getName(),eleID)
    if obj.isUnmarked():
        obj.markObject()
        cleanup = False
        if obj.getErr() != '': #will be an entry node
            dot.node(eleID,eleName,color='red')
            cleanup = True
        else:
            dot.node(eleID,eleName)
        childlist = obj.getChildren()
        for child in childlist:
            cname = str(child.getName())
            c = dotGen(dot,child,reqDict,KEYs)
            dot.edge(eleID,c)
            if cleanup:
                assert cname in KEYs
                eleList = KEYs[cname]
                tempele = eleList[0]
                eleList.remove(tempele)
    if max_seq_no < eleSeqNo:
        max_seq_no = eleSeqNo
    return eleID

def makeDot(reqDict,KEYs):
    global max_seq_no
    dot = Digraph(comment='Spot',format='pdf')
    for key in reqDict:
        obj = reqDict[key]
        max_seq_no = obj.getSeqNo() #set the min seq number for this subtree
        pID = str(max_seq_no)
        if obj.isUnmarked():
            obj.markObject()
            cleanup = False
            childlist = obj.getChildren()
            for child in childlist:
                cID = dotGen(dot,child,reqDict,KEYs)
                dot.edge(pID,cID)
                cname = child.getName()
                if cleanup: #remove name from KEYs so that we don't count it as an unused_write
                    assert cname in KEYs
                    eleList = KEYs[cname]
                    tempele = eleList[0]
                    eleList.remove(tempele)
            node_name = '{}\\nseq:{}-{},dur:{}ms'.format(obj.getName(),pID,max_seq_no,obj.getDuration())
            if obj.getErr() != '':
                dot.node(pID,node_name,color='red')
                cleanup = True
            else:
                dot.node(pID,node_name)
    dot.render('spotgraph', view=True)
    return

def parseIt(event):
    fname = None
    reqDict = {} #dictionary holding request (DictEle) objects by requestID
    SEQs = {} #dictionary by seqID holding DictEles, for easy traversal by seqNo
    KEYs = {} #dictionary by name (key) for DictEles, popped when assigned by earliest ts
    #check that the file is available 
    fname = None
    if 'fname' in event:
        fname = event['fname']
        if not os.path.exists(fname) or not os.path.isfile(fname):
            fname = None
    if not fname:
        print('Unable to find/open file in parseIt')
        return
    if DEBUG:
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
        process(item,reqDict,SEQs,KEYs)
    makeDot(reqDict,KEYs)
    if missed_count != 0 or len(missing) != 0:
        print("missed_count: {}, objs missing {}".format(missed_count,len(missing)))
    if invoke_calls != invokes:
        print("invoked_count: {}, invokes {}".format(invoke_calls,invokes))
    print("requests_count: {}".format(counter))
    print("unused_writes:")
    counter = 0
    for key in KEYs:
        eleList = KEYs[key]
        for ele in eleList:
            print("\t{}:{}".format(key,ele.getSeqNo(),ele.getName()))
            counter += 1
    print("unused_writes: {}".format(counter))
    print("total_order:")
    for pair in sorted(SEQs.items(), key=lambda t: get_key(t[0])):
        ele = pair[1]
        print(pair[0],ele.getName())

def get_key(key):
    try:
        return int(key)
    except ValueError:
        return key
    

class DictEle:
    __seqNo = 0

    #def addChild(self,child,childtype):
        #if childtype not in self.__children_lists:
            #self.__children_lists[childtype] = []
        #self.__children_lists[childtype].append(child)
    def addChild(self,child):
        if child not in self.__children:
            self.__children.append(child)
    def markObject(self):
        self.__color = Color.BLACK
    def unmarkObject(self):
        self.__color = Color.WHITE
    def isUnmarked(self):
        return self.__color == Color.WHITE
    def setDuration(self,duration):
        self.__duration = duration
    def getDuration(self):
        return self.__duration
    def setErr(self,error):
        self.__error = error
    def getErr(self):
        return self.__error
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
    def getChildren(self):
        return self.__children
    def getSourceIP(self):
        if 'sourceIP' in self.__ele:
            return self.__ele['sourceIP']['S']
        else:
            return "unknown"

    def __init__(self,blob,reqID,name,nm,ts):
        #self.__children_lists = {} #list of DictEles per Names.enum
        self.__color = Color.WHITE
        self.__children = []
        self.__seq = self.getAndIncrSeqNo()
        self.__ts = ts
        self.__nm = nm
        self.__name = name
        self.__reqID = reqID
        self.__duration = 0
        self.__error = ''
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
    if args.fname_is_dbdump: #use the dbdump file instead of the DB event stream
        event['oldversion'] = 'any text will work'
    #event['schema'] = args.schema
    parseIt(event)

