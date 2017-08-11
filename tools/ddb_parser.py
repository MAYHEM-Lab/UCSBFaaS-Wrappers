import json,time,os,sys,argparse
import ast
from graphviz import Digraph
from pprint import pprint
from enum import Enum

DEBUG = True
Names = Enum('Names','FN S3R S3W DBR DBW SNS GW')
Color = Enum('Color','WHITE GRAY BLACK')
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
        assert req in reqDict
        parent_obj = reqDict[req]
        assert parent_obj.getDuration() == 0
        parent_obj.setDuration(duration)
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
            parent_obj = KEYs.pop(name,None) #assumes 1 S3W apicall triggers only 1 function, todo fix this!
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
            parent_obj = KEYs.pop(name,None) #assumes 1 SNS apicall triggers only 1 function, todo fix this!
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
            print('\tAPICall:',req,reqStr,nm,name)
            #possible function trigger (writes only trigger lambdas in S3, DynamoDB, and SNS
            #store them in KEYs but just keep the last one (most recent) as events are in order
            #if processed from the stream
            ele = DictEle(obj,req,name,nm,ts)
            seq = ele.getSeqNo()
            assert seq not in SEQs
            SEQs[seq] = ele #keep map by seqNo
            parent_obj.addChild(ele)
            if DEBUG:
                print('\tAdding child name: {}, to name {}'.format(ele.getName(),parent_obj.getName()))
            #assert name not in KEYs #if exact key and value is in dict, overwrite it with more recent ele
            #if no function consumed the event, we must move on
            KEYs[name] = ele #store for later use, overwrite last key (processing in sequence order)

        if nm == Names.FN:
            skipInvoke = True
    
def dotGen(dot,obj,reqDict):
        eleID = str(obj.getSeqNo())
        eleName = str(obj.getName())
        if obj.isUnmarked():
            obj.markObject()
            dot.node(eleID,eleName)
            childlist = obj.getChildren()
            for child in childlist:
                c1 = str(child.getName())
                c = dotGen(dot,child,reqDict)
                dot.edge(eleID,c)
        return eleID

def makeDot(reqDict):
    dot = Digraph(comment='Spot',format='pdf')
    for key in reqDict:
        obj = reqDict[key]
        p = str(obj.getSeqNo())
        p1 = str(obj.getName())
        if obj.isUnmarked():
            obj.markObject()
            dot.node(p,p1)
            childlist = obj.getChildren()
            for child in childlist:
                c1 = str(child.getName())
                c = dotGen(dot,child,reqDict)
                dot.edge(p,c)
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
        #if counter > 10:
            #break
        #if DEBUG:
            #print(item)
        process(item,reqDict,SEQs,KEYs)
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

