import json,time,os,sys,argparse
import ast
from graphviz import Digraph
from pprint import pprint
from enum import Enum

DEBUG = True
Names = Enum('Names','FN S3R S3W DBR DBW SNS GW')
invokes = 0
def getName(n):
    global invokes
    if n.startswith('Invoke:'):
        invokes += 1 #just count, don't create
    if n == 'entry' or n.startswith('Invoke:'):
        return Names.FN
    if n.startswith('GetObject:') or n.startswith('ListObjects:'):
        return Names.S3R
    if n.startswith('PutObject:'):
        return Names.S3W
    if n.startswith('PutItem:'):
        return Names.DBW
    if n.startswith('GetItem:'):
        return Names.DBR
    if n.startswith('Publish:'):
        return Names.SNS
    return None

def makeEle(blob,req,nm,reqStr):
    name = None
    es = blob['eventSource']['S']
    ts = int(blob['ts']['N'])
    msg = blob['message']['S']
    preq = None
    if nm == Names.FN:
        if reqStr == 'entry':
            #who invoked this function?
            if es.find('ext:invokeCLI') != -1:  #external agent
                arn = blob['thisFnARN']['S'].split(':')
                name = 'FN:{}:{}'.format(arn[6],req)
            else:
                #eventOp = 'invoke' if an invoke event (only used in debugging)
                idx = es.find('lib:invokeCLI:') #lib call from another lambda
                if idx != -1: 
                    tmp1 = es[idx+14:].split(':')
                    caller_fname = 'FN:{}'.format(tmp1[0])
                    preq = '{}'.format(tmp1[1])
                    arn = blob['thisFnARN']['S'].split(':')
                    name = 'FN:{}:{}'.format(arn[6],req)
                else:
                    print('Error: expected to find invokeCli in msg: {}'.format(msg))
        else:
            idx = msg.find('SW:FunctionName:')
            if idx != -1:
                name = 'FN:{}'.format(msg[idx+16:])
            else:
                print('Error: expected to find FunctionName in msg: {}'.format(msg))

    elif nm == Names.S3R:
        idx = msg.find('SW:Bkt:')
        if idx != -1:
            idx2 = msg.find(':Key:')
            if idx2 != -1:
                name = 'S3R:{}:{}'.format(msg[idx+7:idx2],msg[idx2+6:])
            else:
                print('Error: expected to find :Key: in msg: {}'.format(msg))
        else:
            idx = msg.find('ListObjects:')
            if idx != -1:
                rest = msg[idx+12:]
                rest = ast.literal_eval(rest)
                name = 'S3R:{}:{}'.format(rest['Bucket'],rest['Prefix'])
            else:
                print('Error: expected to find SW:Bkt or :ListObjects: in msg: {}'.format(msg))
		
    elif nm == Names.S3W:
        idx = msg.find('SW:Bkt:')
        if idx != -1:
            idx2 = msg.find(':Key:')
            if idx2 != -1:
                name = 'S3W:{}:{}'.format(msg[idx+7:idx2],msg[idx2+5:])
            else:
                print('Error2: expected to find :Key: in msg: {}'.format(msg))
        else:
            print('Error2: expected to find SW:Bkt: in msg: {}'.format(msg))
    elif nm == Names.DBR:
        idx = msg.find('SW:TableName:')
        if idx != -1:
            idx = msg.find(':Key:')
            if idx != -1:
                name = 'DBR:{}:{}'.format(msg[idx+13:idx2],msg[idx2+5:])
            else:
                print('Error3: expected to find Key: in msg: {}'.format(msg))
        else:
            print('Error3: expected to find SW:TableName: in msg: {}'.format(msg))
    elif nm == Names.DBW:
        idx = msg.find('SW:TableName:')
        if idx != -1:
            idx = msg.find(':Item:')
            if idx != -1:
                name = 'DBW:{}:{}'.format(msg[idx+13:idx2],msg[idx2+6:])
            else:
                print('Error4: expected to find Item: in msg: {}'.format(msg))
        else:
            print('Error4: expected to find SW:TableName: in msg: {}'.format(msg))
    elif nm == Names.SNS:
        idx = msg.find('SW:sns:Publish:Topic:arn:aws:sns:')
        if idx != -1:
            idx = msg.find(':Subject:')
            if idx != -1:
                name = 'SNS:{}:{}'.format(msg[idx+33:idx2],msg[idx2+9:])
            else:
                name = 'SNS:{}'.format(msg[idx+33:])
        else:
            print('Error5: expected to find SW:sns:Publish:Topic: in msg: {}'.format(msg))
    elif nm == Names.GW:
        pass
    else:
        assert False
    if name:
        ele = DictEle(blob,req,name)
    else:
        ele = DictEle(blob,req,nm)
    return ele,preq

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

    #decode the json file
    data = None
    with open(fname) as data_file:    
        data = json.load(data_file)
    if not data:
        return

    count = data['Count']
    #put them in sorted order by timestamp
    reqs = sorted(data['Items'], key=lambda k: k['ts'].get('N', 0))
    counter = 0
    missed_count = 0
    missing = {}
    for item in reqs:
        counter += 1
        #if counter > 10:
            #break
        if DEBUG:
            print(item)
        reqblob = item['requestID']['S'].split(':')
        req = reqblob[0]
        reqStr = reqblob[1]
        if len(reqblob) > 2:
            reqStr += ':{}'.format(reqblob[2])
            assert len(reqblob)<=3
        ts = float(item['ts']['N'])

        nm = getName(reqStr)
        if not nm: #process the exit or its an invoke (just count it)
            assert req in reqDict
            if reqStr == 'exit': 
                #update timings only
                ele = reqDict[req]
                ele.endTime(item['duration'])
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

    makeDot(reqDict)
    print("missed_count: {}, invoke events: {}, objs missing {}".format(missed_count,invokes,len(missing)))

class DictEle:
    __seqNo = 0

    def addChild(self,child,childtype):
        if childtype not in self.children_lists:
            self.children_lists[childtype] = []
        self.children_lists[childtype].append(child)
    def endTime(self,duration):
        self.duration = duration
    def getBlob(self):
        return self.ele
    def getName(self):
        return self.name
    def getSeqNo(self):
        return self.seq
    def getReqId(self):
        return self.reqID

    def __init__(self,blob,reqID,name):
        self.children_lists = {} #list of DictEles per Names.enum
        self.seq = self.getAndIncrSeqNo()
        print('set seq {}'.format(self.seq))
        self.name = name
        self.reqID = reqID
        self.duration = 0
        self.ele = blob

    @staticmethod
    def getAndIncrSeqNo(incr=1):
        seqno =  DictEle.__seqNo
        DictEle.__seqNo += incr
        return seqno

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DynamoDB spotFns Table data Parser')
    parser.add_argument('fname',action='store',help='filename to process')
    #parser.add_argument('schema',action='store',help='schema of file to process')
    args = parser.parse_args()
    event = {}
    event['fname'] = args.fname
    #event['schema'] = args.schema
    parseIt(event)

