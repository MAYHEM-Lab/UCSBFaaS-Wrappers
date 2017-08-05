import json,time,os,sys,argparse
from pprint import pprint
from enum import Enum

DEBUG = True
Names = Enum('Names','FN S3R S3W DBR DBW SNS GW')
def getName(n):
    if n == 'entry' or n.startswith('Invoke:'):
        return DictEle.Names.FN
    if n.startswith('GetObject:') or n.startswith('ListObjects:'):
        return DictEle.Names.S3R
    if n.startswith('PutObject:'):
        return DictEle.Names.S3W
    if n.startswith('PutItem:'):
        return DictEle.Names.DBW
    if n.startswith('GetItem:'):
        return DictEle.Names.DBR
    if n.startswith('Publish:'):
        return DictEle.Names.SNS
    return None

def makeEle(blob,nm):
    es = blob['eventSource']['S']
    if es.find('int:invokeCLI') or es.find('lib:invokeCLI'):
        print('Found one! {}'.format(es))
    if nm == Names.FN:
        pass
    elif nm == Names.S3R:
        pass
    elif nm == Names.S3W:
        pass
    elif nm == Names.DBR:
        pass
    elif nm == Names.DBW:
        pass
    elif nm == Names.SNS:
        pass
    elif nm == Names.GW:
        pass
    else:
        assert False
    ele = DictEle(item,nm)
    return ele

def parseIt(event):
    OK = False
    fname = schema = None
    reqDict = {} #dictionary holding request (DictEle) objects by requestID

    #check that the file is available 
    if 'fname' in event:
        fname = event['fname']
        print('processing file: {}'.format(fname))
        if os.path.exists(fname) and os.path.isfile(fname):
            OK = True
    if not OK: 
        print('Unable to find/open file in parseIt: {}'.format(fname))
        return

    #decode the json file
    data = None
    with open(fname) as data_file:    
        data = json.load(data_file)
    if not data:
        return

    count = data['Count']
    #put them in sorted order by timestamp
    reqs = sorted(data['Items'], key=lambda k: k['ts'].get('N', 0))
    #pprint(reqs)
    for item in reqs:
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
        if not nm: #process the exit
            assert reqStr == 'exit'
            assert req in reqDict
            #update timings only
            ele = reqDict[req]
            ele.endTime(item['duration'])

        if req not in reqDict:
            assert reqStr == 'entry'
            ele = DictEle(item,nm)
            reqDict[req] = ele
        else:
            assert reqStr != 'entry'
            child = DictEle(item,nm)
            ele = reqDict[req]
            ele.addChild(child)
            if reqStr == 'exit':
                pass #update timings only

class DictEle:
    __seqNo = 0
    Names = Enum('Names','FN S3R S3W DBR DBW SNS GW')

    def addChild(self,child):
        self.children.append(child)
    def endTime(self,duration):
        self.duration = duration

    def __init__(self,blob,name):
        self.children = [] #list of DictEles
        self.seq = self.getSeqNo()
        self.incrSeqNo()
        self.name = name
        self.duration = 0
        self.ele = blob

    @staticmethod
    def getSeqNo():
        return DictEle.__seqNo

    @staticmethod
    def incrSeqNo(incr=1):
        DictEle.__seqNo += incr

        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DynamoDB spotFns Table data Parser')
    parser.add_argument('fname',action='store',help='filename to process')
    #parser.add_argument('schema',action='store',help='schema of file to process')
    args = parser.parse_args()
    event = {}
    event['fname'] = args.fname
    #event['schema'] = args.schema
    parseIt(event)

