import json,time,os,sys,argparse
import ast,statistics
from graphviz import Digraph
from pprint import pprint
from enum import Enum

DEBUG = True
Names = Enum('Names','INV FN S3R S3W DBR DBW SNS GW')
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
        nm =  Names.INV
    else:
        print(n,msg)
        assert False
    ######## process nm #########
    name = None
    if nm == Names.INV:
        idx = msg.find('SW:FunctionName:')
        if idx != -1:
            tname = msg[idx+16:]
            if 'arn:aws:lambda' in msg:
                tname = tname.split(":")[6]
            name = 'INV:{}'.format(tname)
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
        tmp = msg[idx+13:]
        idx = tmp.find(':')
        tname = tmp[:idx]
        if idx != -1:
            idx2 = msg.find(':Key:')
            if idx2 != -1:
                rest = ast.literal_eval(msg[idx2+5:]) #turn it into a dictionary
                name = 'DBR:{}'.format(tname)
                for k in rest:
                    val = rest[k]
                    name += ':{}:{}'.format(k,val)
            else:
                print('Error3: expected to find Key: in msg: {}'.format(msg))
                assert False
        else:
            print('Error3: expected to find SW:TableName: in msg: {}'.format(msg))
            assert False
    elif nm == Names.DBW: 
        idx = msg.find('SW:TableName:')
        tmp = msg[idx+13:]
        idx = tmp.find(':')
        tname = tmp[:idx]
        if idx != -1:
            idx2 = msg.find(':Item:')
            if idx2 != -1:
                rest = ast.literal_eval(msg[idx2+6:]) #turn it into a dictionary
                name = 'DBW:{}'.format(tname)
                for k in rest:
                    val = rest[k]
                    name += ':{}:{}'.format(k,val)
            else:
                print('Error4: expected to find Item: in msg: {}'.format(msg))
                assert False
        else:
            print('Error4: expected to find SW:TableName: in msg: {}'.format(msg))
            assert False
    elif nm == Names.SNS:
        idx = msg.find('sns:Publish:Topic:arn:aws:sns:')
        if idx != -1:
            adder = 1 if 'SW:sns:Publish' in msg else 0 #handle old missing colon entries
            smsg = msg.split(':')
        
            topic = smsg[8+adder]
            subject = ""
            if ':Subject:' in msg:
                subject = ':{}'.format(smsg[10+adder])
            message = ""
            if ':Message:' in msg:
                message = ':{}'.format(smsg[12+adder])
            name = 'SN:{}{}{}'.format(topic,subject,message)
        else:
            print('Error5: expected to find Notification in msg: {}'.format(msg))
            assert False
    else:
        assert False
    return nm,name

################# process #################
def process(obj,reqDict,SEQs,KEYs,IMPLIED_PARENT_ELEs):
    if DEBUG:
        print("processing: {}".format(repr(obj)))
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
    if reqStr.startswith('exit') or reqStr.startswith(':exit'): 
        duration = obj['duration']['N']
        if req in reqDict:
            parent_obj = reqDict[req]
        else:
            parent_obj = IMPLIED_PARENT_ELEs[req]
        assert parent_obj.getDuration() == 0
        parent_obj.setDuration(duration)
        parent_obj.setExitTS(ts)
        #check for error and note it
        err = obj['error']['S']
        if 'SpotWrap_exception' in err:
            parent_obj.setErr(err)
        if DEBUG: 
            print('EXIT: Name: {}, NM: {}, IP: {}'.format(parent_obj.getName(),parent_obj.getNM(),parent_obj.getSourceIP()))
    elif reqStr.startswith('entry') or reqStr.startswith(':entry'):  ############ function entry ##################
        nm = Names.FN            
        if 'thisFnARN' in obj:
            arn = obj['thisFnARN']['S'].split(':')
            name = 'FN:{}:{}'.format(arn[6],req)
        ip = 'unknown'
        if 'sourceIP' in obj:
            ip = obj['sourceIP']['S']
        ele = DictEle(obj,req,name,nm,ts)
        ele.setSourceIP(ip)
        seq = ele.getSeqNo()
        assert seq not in SEQs
        SEQs[seq] = ele #keep map by seqNo
        #only insert it into reqDict if it doesn't have a parent!
        reqDict[req] = ele
        if DEBUG:
            print('ENTRY: Name: {}, NM: {}, IP: {}'.format(ele.getName(),ele.getNM(),ele.getSourceIP()))
        if eventOp.startswith('ObjectRemoved:') or eventOp.startswith('ObjectCreated:'):
            #link to existing Names.S3W object
            msg = obj['message']['S'].split(':')
            name = 'S3W:{}:{}'.format(msg[0],msg[1])
            ele.setTrigger('S3W')
            if name not in KEYs or KEYs[name] == []:
                print('WARNING: S3W triggered function has no parent! {} {}\n\t{}'.format(name,eventOp,es))
            else:
                eleList = KEYs[name]
                parent_obj = None
                for tmpele in eleList:
                    if not parent_obj:
                        parent_obj = tmpele
                    else:
                        if tmpele.getSeqNo() < parent_obj.getSeqNo():
                            #tmpele occured earlier than parent_obj, so use tmpele instead
                            parent_obj = tmpele
                assert parent_obj is not None
                eleList.remove(parent_obj) #same bkt/prefix cannot trigger >1 functions so remove it once used
                if DEBUG:
                    print('\tAdding child name: {}, to name {}'.format(ele.getName(),parent_obj.getName()))
                parent_obj.addChild(ele)
        elif 'lib:invokeCLI' in es:
            #link to existing Names.FN
            idx = es.find('lib:invokeCLI:') #lib call from another lambda
            invokes += 1
            if idx != -1: 
                ele.setTrigger('libInv')
                tmp1 = es[idx+14:].split(':')
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
        elif eventOp.startswith('INSERT') or eventOp.startswith('REMOVE') or eventOp.startswith('MODIFY'):
            ele.setTrigger('DBW')
            #"New:{'name': {'S': 'cjkFInfPy29726'}, 'age': {'S': '18640'}}"
            #":Old:{'name': {'S': 'newkeycjk'}, 'age': {'S': '315'}}"}
            #{'S': "New:{'name': {'S': 'cjkDBModPy1'}, 'age': {'S': '6953'}}:Old:{'name': {'S': 'cjkDBModPy1'}, 'age': {'S': '9943'}}"}
            #'eventSource': {'S': 'arn:aws:dynamodb:us-west-2:443592014519:table/triggerTable/stream/2017-07-30T18:38:23.171'}
            idx = es.find('table/')
            assert idx != -1
            tmp = es[idx+6:]
            idx = tmp.find('/')
            assert idx != -1
            tname = tmp[:idx]
            idx = msg.find('New:') 
            if idx == -1:
                idx = msg.find('Old:') 
            if eventOp.startswith('MODIFY'):
                idx2 = msg.find(':Old:') 
                rest = ast.literal_eval(msg[idx+4:idx2]) #turn it into a dictionary
            else:    
                rest = ast.literal_eval(msg[idx+4:]) #turn it into a dictionary
            name = 'DBW:{}'.format(tname)
            for k in rest:
                val = rest[k]
                if 'S' in val:
                    name += ':{}:{}'.format(k,val['S'])
                elif 'N' in val:
                    name += ':{}:{}'.format(k,val['N'])
                else:
                    print("ERROR: unhandled dynamoDB type: {}".format(val))
                    sys.exit(1)
            if name not in KEYs or KEYs[name] == []:
                print('ERROR: DBW without a DBR: {} {}'.format(name,req))
            else:
                eleList = KEYs[name]
                parent_obj = None
                for tmpele in eleList:
                    assert tmpele is not None
                    if not parent_obj:
                        parent_obj = tmpele
                    else:
                        if tmpele.getSeqNo() > parent_obj.getSeqNo():
                            #get the most recent seq number 
                            parent_obj = tmpele
                assert parent_obj is not None
                #eleList.remove(parent_obj) #don't remove it b/c it can trigger multiple fns
                if DEBUG:
                    print('\tAdding child name: {}, to name {}'.format(ele.getName(),parent_obj.getName()))
                parent_obj.addChild(ele)
        elif eventOp.startswith('Notification'):
            ele.setTrigger('SNS')
            #invoke from SNS notification
            arn = es.split(':') #arn
            topic = arn[5]
            idx = msg.find(':') #subject:rest
            subject = msg[0:idx]
            message = msg[idx+1:]
            #SN:region:acct:topic:subject:Message:msg
            name = 'SN:{}:{}:{}'.format(topic,subject,message)
            assert name in KEYs
            eleList = KEYs[name]
            parent_obj = None
            for tmpele in eleList:
                if not parent_obj:
                    parent_obj = tmpele
                else:
                    if tmpele.getSeqNo() > parent_obj.getSeqNo():
                        #get the most recent seq number 
                        parent_obj = tmpele
            assert parent_obj is not None
            #eleList.remove(parent_obj) #cannot remove bc it can trigger multiple functions
            if DEBUG:
                print('\tAdding child name: {}, to name {}'.format(ele.getName(),parent_obj.getName()))
            parent_obj.addChild(ele)
        elif es.startswith('aws:APIGateway:'):
            #was invoked synchronously by API Gateway; async calls look like invokes (undetectable)
            #{'accountID': {'S': '443592014519'}, 'caller': {'S': 'fd05e16f-812a-11e7-b28c-57b1fcee6bea'}, 'duration': {'N': '0'}, 'error': {'S': 'SpotWrapPython'},'eventOp': {'S': '/test/FnInvokerPy'}, 'eventSource': {'S': 'aws:APIGateway:gf4tjn3199'}, 'message': {'S': 'arn1jb:curl:{ \n    "a":"4",\n    "b":"2",\n    "op":"-"\n}\n'}, 'region': {'S': 'us-west-2'}, 'requestID': {'S': 'fd0a27db-812a-11e7-b727-2d2b9ea53971:entry'}, 'sourceIP': {'S': '98.171.178.234'}, 'thisFnARN': {'S': 'arn:aws:lambda:us-west-2:443592014519:function:FnInvokerPy'}, 'ts': {'N': '1502740733529'}}
            route = eventOp
            caller = obj['caller']['S']
            tmp = es.split(":")
            api = tmp[2]
            ip = 'unknown'
            if 'sourceIP' in obj:
                ip = obj['sourceIP']['S']
            name = 'GW:{}:{}:{}'.format(api,caller,route)
            #create an object from this data and make obj the child of the new object
            child = reqDict.pop(req,None) #remove from reqDict 
            child.setTrigger('GW')
            oldseq = child.getSeqNo() #get old object's sequence number
            SEQs.pop(oldseq) #remove from SEQs 
            ele = DictEle(obj,caller,name,Names.GW,ts) #get new obj and seqNo
            ele.setTrigger('HTTP')
            ele.setSourceIP(ip)
            newseq = ele.getSeqNo() 
            #swap sequence numbers because they are out of order
            ele.setSeqNo(oldseq)
            child.setSeqNo(newseq)
            SEQs[oldseq] = ele #keep map by seqNo
            SEQs[newseq] = child #keep map by seqNo

            #only insert it into reqDict if it doesn't have a parent!
            reqDict[ele] = ele #replace child with caller's seqno
            IMPLIED_PARENT_ELEs[req] = child #need to keep this around in order to update duration via exit
            ele.addChild(child)
        else:
            print('WARNING: function has no parent! {} {}\n{}'.format(name,eventOp,es))
            #assert False
    else: #other event, record it to build trace
        nm, name = processAPICall(reqStr, msg)
        assert req in reqDict
        parent_obj = reqDict[req]
        #if nm == Names.S3W or nm == Names.DBW or nm == Names.SNS:
        if DEBUG:
            print('\tAPICall:',req,reqStr,nm,name)
        #possible function trigger (writes only trigger lambdas in S3, DynamoDB, and SNS)
        ele = DictEle(obj,req,name,nm,ts)
        ele.setTrigger('FnSDK')
        seq = ele.getSeqNo()
        assert seq not in SEQs
        SEQs[seq] = ele #keep map by seqNo
        parent_obj.addChild(ele)
        if DEBUG:
            print('\tAdding child name: {}, to name {}'.format(ele.getName(),parent_obj.getName()))
        #store them in KEYs even if they are duplicate (we will distinguished by sequence No)
        if nm != Names.S3R and nm != Names.DBR and nm != Names.INV:
            assert ele is not None
            KEYs.setdefault(name,[]).append(ele) #store duplicates if any

        if nm == Names.INV:
            skipInvoke = True
    
def dotGen(dot,obj,reqDict,KEYs,parent):
    global max_seq_no
    eleSeqNo = obj.getSeqNo()
    eleID = str(eleSeqNo)
    skipFlag = False #this gets set if INCLUDE_READS is False and we are returning a read node (used to skip making the edge assignment)
    if obj.isUnmarked():
        obj.markObject()
        cleanup = False
        childlist = obj.getChildren()
        for child in childlist:
            cname = str(child.getName())
            c,skipEdge = dotGen(dot,child,reqDict,KEYs,obj)
            if not skipEdge:
                dot.edge(eleID,c)
            if cleanup:
                assert cname in KEYs
                eleList = KEYs[cname]
                tmpele = eleList[0]
                eleList.remove(tmpele)
        duration = obj.getDuration()
        if duration == 0: #for all non-entries this will be 0
            me = obj.getTS()
            #print("TS: {}, entry:{}, me:{}, exit:{}".format(obj.getReqId(),parent.getTS(),me,parent.getExitTS()))
            entry_to_me = int(me - parent.getTS())
            me_to_exit = int(parent.getExitTS() - me)
            eleName = '{}:{}\\nb4:{}ms:after:{}ms'.format(obj.getName(),eleID,entry_to_me,me_to_exit)
            if entry_to_me < 0 or me_to_exit < 0:
                print(eleName)
                assert False
            obj.setDurationTS(entry_to_me)
            obj.setDurationTSExit(me_to_exit)
        else:
            start_ts = obj.getTS()
            end_ts = obj.getExitTS()
            tsdur = int(end_ts-start_ts)
            if tsdur < 0:
                tsdur = 0
            eleName = '{}:{}\\ndur:{}ms:tsdur:{}ms'.format(obj.getName(),eleID,duration,tsdur)
            obj.setDurationTS(tsdur)
        nm = obj.getNM()
        if nm == Names.S3R or nm == Names.DBR or nm == Names.INV:
            if INCLUDE_READS:
                dot.node(eleID,eleName,fillcolor='gray',style='filled')
            else:
                skipFlag = True
        else:
            if nm == Names.FN and obj.getExitTS() == 0:
                dot.node(eleID,eleName,fillcolor='orange',style='filled')
            else:
                dot.node(eleID,eleName)
    if max_seq_no < eleSeqNo:
        max_seq_no = eleSeqNo
    return eleID,skipFlag

def unmarkNodes(SEQs):
    for key in SEQs:
        SEQs[key].unmarkObject()

def getShortName(name):
    sname = name.split(":")
    stype = sname[0]
    #if stype == 'S3W':
        #retn = "{}:{}:{}".format(stype,sname[1],sname[2])
    #else:
        #retn = "{}:{}".format(stype,sname[1])
    retn = "{}_{}".format(stype,sname[1])
    retn = retn.replace('/','_')
    retn = retn.replace('.','_')
    retn = retn.replace('"','')
    print('{} short name: {}'.format(name,retn))
    return retn

def makeDotAggregate(SEQs,reqDict):
    dot = Digraph(comment='SpotAggregate',format='pdf')
    agent_name = "Agent"
    dot.node(agent_name,agent_name)
    final_list = {}
    edge_list = []
    node_list = [agent_name]

    for key in reqDict:
        obj = reqDict[key]
        name = getShortName(obj.getName())
        assert not name.startswith('INV')
        edge = '{}:{}'.format(agent_name,name)
        if edge not in edge_list:
            if name not in node_list:
                node_list.append(name)
                dot.node(name,name)
            dot.edge(agent_name,name)
            edge_list.append(edge)
            print('adding edge: {}'.format(edge))

    for key in SEQs:
        obj = SEQs[key]
        name = getShortName(obj.getName())
        print("processing {}:{}".format(name,obj.getName()))
        durlist = []
        durTslist = []
        ccountlist = []
        clist = []
        tupl = None
        if name in final_list:
            tupl = final_list[name]
            clist = tupl[3]
            durlist = tupl[0]
            durTslist = tupl[1]
            ccountlist = tupl[2]
            print("FOUND an old one")
        childlist = obj.getChildren()
        for child in childlist:
            nm = getShortName(child.getName())
            if nm not in clist:
                clist.append(nm)
        durlist.append(float(obj.getDuration()))
        durTslist.append(float(obj.getDurationTS()))
        ccountlist.append(float(len(clist)))
        print("here: {} {} {}".format(durlist,durTslist,ccountlist))
        newtupl = (durlist, durTslist, ccountlist, clist)
        print("here: adding {} to final_list: {}".format(name,newtupl))
        final_list[name] = newtupl

    for n in final_list:
        tupl = final_list[n]
        avgdur = statistics.mean(tupl[0])
        avgdurTS = statistics.mean(tupl[1])
        avgChildCount = statistics.mean(tupl[2])

        stdevdur = 0.0
        stdevdurTS = 0.0
        stdevChildCount = 0.0
        if len(tupl[0])>1:
            stdevdur = statistics.stdev(tupl[0])
        if len(tupl[1])>1:
            stdvdurTS = statistics.stdev(tupl[1])
        if len(tupl[2])>1:
            stdevChildCount = statistics.stdev(tupl[2])

        if n not in node_list:
            if n.startswith('INV'):
                continue
            label = "{}\\n{:.1f}:{:.1f}:{:.1f}".format(n,avgdur,avgdurTS,avgChildCount)
            if n.startswith('DBR') or n.startswith('S3R') or n.startswith('INV'):
                dot.node(n,label,fillcolor='gray',style='filled')
            else:
                dot.node(n,label)
            node_list.append(n) 
        clist = tupl[3]
        for cn in clist:
            if cn.startswith('INV'):
                continue
            edge = '{}:{}'.format(n,cn)
            if edge not in edge_list:
                if name not in node_list:
                    node_list.append(cn)
                    if cn.startswith('DBR') or cn.startswith('S3R') or cn.startswith('INV'):
                        dot.node(cn,cn,fillcolor='gray',style='filled')
                    else:
                        dot.node(cn,cn)
                dot.edge(n,cn)
                edge_list.append(edge)
    dot.render('spotagggraph', view=True)
    return

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
                cID,skipEdge = dotGen(dot,child,reqDict,KEYs,obj)
                if not skipEdge:
                    dot.edge(pID,cID)
                cname = child.getName()
                if cleanup: #remove name from KEYs so that we don't count it as an unused_write
                    assert cname in KEYs
                    eleList = KEYs[cname]
                    tmpele = eleList[0]
                    eleList.remove(tmpele) #ok to remove at this point
            #root notes are functions and so they have a duration
            start_ts = obj.getTS()
            end_ts = obj.getExitTS()
            tsdur = int(end_ts-start_ts)
            if tsdur < 0:
                tsdur = 0
            node_name = '{}\\nseq:{}-{},dur:{}ms,tsdur:{}ms'.format(obj.getName(),pID,max_seq_no,obj.getDuration(),tsdur)
            obj.setDurationTS(tsdur)
            err = obj.getErr()
            if err != '': #only set for entry nodes
                idx = err.find('exception:')
                if idx == -1:
                    idx = 0
                else:
                    idx = idx+10
                end = len(err)
                if end > 100:
                    end = 100
                node_name = '{}\\nerr:{}'.format(node_name,err[idx:end])
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
    IMPLIED_PARENT_ELEs = {} #dictionary by req holding DictEles for those for which we make new parents (APIGatway objects and 
    KEYs = {} #dictionary by name (key) for DictEles, popped when assigned by earliest ts
    #check that the file is available 
    processAll = False
    if 'process_all' in event:
        processAll = True
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
    last_remove_count = -1
    if not processAll:
        with open(fname) as data_file:    
            #first check for modifies and find the last remove entry
            for line in data_file:
                count += 1
                if 'REMOVE:' in line:
                    last_remove_count = count
        print('last_remove_count: {}'.format(last_remove_count))
            
    with open(fname) as data_file:    
        count = 0
        for line in data_file:
            count += 1
            if processAll or count >= last_remove_count:
                if 'MODIFY:' in line:
                    print("ERROR, there should be no modifies!:")
                    print(line)
                #get item object = seqNo INSERT:yyy:{item}
                idx = line.find('INSERT:') 
                if idx != -1: #skip the REMOVE entries
                    ln = line[idx:]
                    idx = ln.find(':')
                    idx = ln.find(':',idx+1)
                    rest = ast.literal_eval(ln[idx+1:]) #turn it into a dictionary
                    reqs.append(rest)
    
    count = len(reqs)
    counter = 0
    missed_count = 0
    missing = {}
    for item in reqs:
        counter += 1
        process(item,reqDict,SEQs,KEYs,IMPLIED_PARENT_ELEs)
    #makeDot(reqDict,KEYs)
    #unmarkNodes(SEQs)
    makeDotAggregate(SEQs,reqDict) #todo, add missing parents support (catch WARNINGs)

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
    counter = 1
    for pair in sorted(SEQs.items(), key=lambda t: get_key(t[0])): #(seqNo,DictEle) pairs sorted by seqNo
        ele = pair[1]
        nm = ele.getNM()
        if INCLUDE_READS:
            counter = pair[0]
        else:
            if nm == Names.S3R or nm == Names.DBR or nm == Names.INV:
                continue
            counter += 1 #need to use a counter because pair[0] (the seqNo) includes reads
        print('{}:{}:{}:{}:{}:{}:{}'.format(counter,ele.getName(),nm,ele.getDuration(),ele.getDurationTS(),ele.getDurationTSExit(),ele.getTrigger()))

def get_key(key):
    try:
        return int(key)
    except ValueError:
        return key
    
class DictEle:
    __seqNo = 0

    def addChild(self,child):
        if child not in self.__children:
            self.__children.append(child)
    def markObject(self):
        self.__color = Color.BLACK
    def unmarkObject(self):
        self.__color = Color.WHITE
    def isUnmarked(self):
        return self.__color == Color.WHITE
    def setExitTS(self,ts):
        self.__exit_ts = ts
    def getExitTS(self):
        return self.__exit_ts
    def getTS(self):
        return self.__ts
    def setDuration(self,duration):
        self.__duration = duration
    def getDuration(self):
        return self.__duration
    def setDurationTS(self,duration):
        self.__duration_ts = duration
    def getDurationTS(self):
        return self.__duration_ts
    def setDurationTSExit(self,duration):
        self.__duration_tsexit = duration
    def getDurationTSExit(self):
        return self.__duration_tsexit
    def setErr(self,error):
        self.__error = error
    def getErr(self):
        return self.__error
    #def getBlob(self):
        #return self.__ele
    def getName(self):
        return self.__name
    def getSeqNo(self):
        return self.__seq
    def setSeqNo(self,seqno):
        self.__seq = seqno
    def setTrigger(self,trigger):
        self.__trigger = trigger
    def getTrigger(self):
        return self.__trigger
    def getReqId(self):
        return self.__reqID
    def getNM(self):
        return self.__nm
    def getChildren(self):
        return self.__children
    def getSourceIP(self):
        return self.__source_ip
    def setSourceIP(self,source_ip):
        self.__source_ip = source_ip

    def __init__(self,blob,reqID,name,nm,ts):
        #self.__children_lists = {} #list of DictEles per Names.enum
        self.__color = Color.WHITE
        self.__children = []
        self.__seq = self.getAndIncrSeqNo()
        self.__trigger = None
        self.__ts = ts
        self.__nm = nm
        self.__name = name
        self.__reqID = reqID
        self.__duration = 0
        self.__duration_ts = 0
        self.__duration_tsexit = 0
        self.__error = ''
        self.__exit_ts = 0
        if 'sourceIP' in blob:
            self.__source_ip =  blob['sourceIP']['S']
        else: 
            self.__source_ip = "unknown"
        #self.__ele = blob

    @staticmethod
    def getAndIncrSeqNo(incr=1):
        seqno =  DictEle.__seqNo
        DictEle.__seqNo += incr
        return seqno

if __name__ == "__main__":
    global INCLUDE_READS
    parser = argparse.ArgumentParser(description='DynamoDB spotFns Table data Parser')
    parser.add_argument('fname',action='store',help='filename to process')
    parser.add_argument('--process_entire_file',action='store_true',default=False,help='process the entire file instead of skipping to right after the last REMOVE entry which results from the clean')
    parser.add_argument('--fname_is_dbdump',action='store_true',default=False,help='file is dbdump file')
    parser.add_argument('--include_reads',action='store_true',default=False,help='include API reads (non-triggers) in output')
    #parser.add_argument('schema',action='store',help='schema of file to process')
    args = parser.parse_args()
    event = {}
    INCLUDE_READS = args.include_reads
    event['fname'] = args.fname
    if args.fname_is_dbdump: #use the dbdump file instead of the DB event stream
        event['oldversion'] = 'any text will work'
    if args.process_entire_file: 
        event['process_all'] = 'any text will work'
    parseIt(event)

