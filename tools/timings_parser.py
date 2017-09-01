import json,time,os,sys,argparse,statistics
from pprint import pprint
from enum import Enum

DEBUG = True
STATUS_LIST = [200.0,202.0,400.0]
#FILE_LIST = ["coord.log","driv.log","map.log","s3mod.log","spottemp.log","dbmod.log","fninv.log","red.log","sns.log"]
FILE_LIST = ["coord.log","driv.log","map.log","red.log"]
def check_dir(dir_key,event,job):
    '''
    Check that the dirs and files exist (return True if so, else print error and return False)
    '''
    retn = False
    prefixes = ['1','2','3','4','5','6','7','8','9','10']
    if dir_key in event:
        cdir = event[dir_key]
        if not os.path.exists(cdir):
            print('Error, directory {} not found (unable to proceed)'.format(cdir))
            return True
        retn = True
        if not os.path.isdir(cdir):
            print('Error, {} is not a directory (unable to proceed)'.format(cdir))
            return True
        lst = os.listdir(cdir)
        for f in prefixes:
            if job=='SPOT' or job=='BOTH':
                if f not in lst:
                    #list all of the missing ones for the user
                    print('Error, {}/{} not found (unable to proceed)'.format(cdir,f))
                    retn = False
            nscdir = '{}/{}/NS'.format(cdir,f)
            if (job=='NS' or job=='both') and not os.path.isdir(cdir):
                print('Error, {}/{} not found (unable to proceed)'.format(cdir,f))
                retn = False
    return retn
        
def processCW(dirname,jobcount,NSJob,ofile,skipFirst=False):
    '''      coord.log    driv.log     map.log      s3mod.log    spottemp.log
	     dbmod.log    fninv.log    red.log      sns.log
    lines: 
    Fn:reqID:duration_billed:mem_used	//Record
    Fn:reqID:duration_measured_for_this_fn:status_reported_by_call  //SpotWrap for wrapped fn

    Others:
    Fn:reqID:duration_measured_for_this_fn:duration_measured_for_invoke:status=202  //SDK Invoke (FnInvoker, SpotTemplatePy)
    Fn:reqID:duration			//Self (FnInvoker or SpotTemplatePy)

    EX:
    /aws/lambda/reducerCoordinator:70361a64-7fa3-11e7-87b5-29bd2e211f42:1108.58:67.0
    '''
    fnames = [] 

    #ns_str = '/NS' if NSJob else ''
    #for n in range(1,jobcount+1):
        #if n > 1 or not skipFirst:
            #fnames.append('{}/{}{}/'.format(dirname,n,ns_str)) #dirnames

    fnames.append('{}/11/APP/'.format(dirname)) #dirnames
    #for each file, collect job timings for each for jobcount runs
    for postfix in FILE_LIST:
        tlist = []
        swlist = []
        mlist = []
        swcount = count = 0
        for fname in fnames:
            fname += postfix
            with open(fname,'r') as f:
                for line in f:
                    if line.startswith('No streams'):
                        break
                    line = line.strip()
                    strs = line.split(':')
                    if len(strs) != 4: #only process Record and SpotWrap values for now
                        continue
                    fn = strs[0]
                    req = strs[1]
                    if float(strs[3]) in STATUS_LIST:
                        assert not NSJob
                        #SpotWrap entry = Fn:reqID:duration_measured_for_this_fn:status_reported_by_call  
                        if DEBUG:
                            print('SW Entry')
                        swlist.append(float(strs[2]))
                        swcount += 1
                    else:
                        #Fn:reqID:duration_billed:mem_used	//Record
                        tlist.append(float(strs[2]))
                        mlist.append(float(strs[3]))
                        count += 1
                        
        if count > 0:
            if swcount > 0: #TODO clean this up once working as swcount will =0 when NSJob is false
                print('{}:{}:{}:{}:{}:{}:{}:{}'.format(
                    postfix,count,
                    statistics.mean(tlist),statistics.stdev(tlist),
                    statistics.mean(swlist),statistics.stdev(swlist),
                    statistics.mean(mlist),statistics.stdev(mlist)
                ))
            else:
                if count > 1:
                    print('{}:{}:{}:{}:{}:{}:{}:{}'.format(
                        postfix,count,
                        statistics.mean(tlist),statistics.stdev(tlist),0.0,0.0,
                        statistics.mean(mlist),statistics.stdev(mlist)
                    ))
                else:
                    print('{}:{}:{}:{}:{}:{}:{}:{}'.format(
                        postfix,count,
                        statistics.mean(tlist),0.0,0.0,0.0,
                        statistics.mean(mlist),0.0
                    ))
        else:
            print('{}:{}:{}:{}:{}:{}:{}:{}'.format(
                postfix,0,0.0,0.0,0.0,0.0,0.0,0.0))

def processDB(dirname,jobcount,NSJob,ofile,skipFirst=False):
    pass
def processMR(dirname,jobcount,NSJob,ofile,skipFirst=False):
    fnames = []
    ns_str = '' #=2 Spot
    if NSJob == 1:
        ns_str = '/NS'
    elif NSJob == 3: #Fleece
        ns_str = '/F'
    elif NSJob == 4: #GammaRay
        ns_str = '/GR'
    for n in range(1,jobcount+1):
        if n > 1 or not skipFirst:
            fnames.append('{}/{}{}/overhead.out'.format(dirname,n,ns_str)) #file names
    dsize = 0.0
    keycount = 0
    keys = 0 #unused
    lines = 0 #unused
    timer = 0.0
    err = None
    ids = 0
    tlist = []
    for fname in fnames:
        if not os.path.exists(fname):
            print('processMR: Error: {} not found!'.format(fname))
            print('Not processing NSJob ID {}'.format(NSJob))
            return 0,0,0,0,0,0
        ids += 1
        with open(fname,'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('Dataset size'):
                    sline = line.split(' ')
                    dsize = float(sline[2].strip(','))
                    keycount = int(sline[4].strip(','))
                if line.startswith('Num. of Mappers'):
                    sline = line.split(' ')
                    mappers = int(sline[6])
                if line.startswith('mapper output'):
                    sline = line.split(' ')
                    if NSJob == 1 or NSJob == 3: #NS or Fleece
                        keys = int(sline[2].strip('[,'))
                        lines = int(sline[3].strip(','))
                        timer = float(sline[4].strip(','))
                        err = sline[5].strip("']")
                    else:
                        keys = int(sline[5].strip('[,'))
                        lines = int(sline[6].strip(','))
                        timer = float(sline[7].strip(','))
                        err = sline[8].strip("']}")
                    if err == '': 
                        err = None
                    if not err:
                        tlist.append(timer)
    return (ids,statistics.mean(tlist),statistics.stdev(tlist),mappers,dsize,keycount)
    
def parseIt(event,job='both',skipFirst=False,mrOnly=False):
    '''
    Parse the files output from an overhead job
    '''
    if not check_dir('mrdir',event,job) or not check_dir('dbdir',event,job) or not check_dir('cwdir',event,job):
        print('check_dir failed, exiting...')
        sys.exit(1)

    if 'output_fname' not in event:
        print('no output file name specified, exiting...')
        sys.exit(1)

    with open(event['output_fname'],'w') as ofile: #first to open so overwrite and start fresh
        print()
        if job=='NS' or job=='BOTH': #1=NS
            count,avg,stdev,mcount,dsize,keys = processMR(event['mrdir'],event['count'],1,ofile,skipFirst)
            print('NStotal:{},map_avg:{}:map_stdev:{}:map_count:{}:dsize:{}:keys:{}'.format(count,avg,stdev,mcount,dsize,keys))
        if job=='SPOT' or job=='BOTH': #2=Spot
            count,avg,stdev,mcount,dsize,keys = processMR(event['mrdir'],event['count'],2,ofile,skipFirst)
            print('SPOTtotal:{},map_avg:{}:map_stdev:{}:map_count:{}:dsize:{}:keys:{}'.format(count,avg,stdev,mcount,dsize,keys))
        #3 = fleece
        count,avg,stdev,mcount,dsize,keys = processMR(event['mrdir'],event['count'],3,ofile,skipFirst)
        print('Fleecetotal:{},map_avg:{}:map_stdev:{}:map_count:{}:dsize:{}:keys:{}'.format(count,avg,stdev,mcount,dsize,keys))
        #4 = GammaRay
        count,avg,stdev,mcount,dsize,keys = processMR(event['mrdir'],event['count'],4,ofile,skipFirst)
        print('GammaRaytotal:{},map_avg:{}:map_stdev:{}:map_count:{}:dsize:{}:keys:{}'.format(count,avg,stdev,mcount,dsize,keys))

        if not mrOnly: 
            ############### Cloudwatch Log Summaries #################
            print('\nCloudwatch Log Data\n\tname,count,billed_avg,billed_stdev,inner_avg,inner_stdev,mem_avg,mem_stdev')
            print('NoSpot:')
            if job=='NS' or job=='BOTH':
                processCW(event['cwdir'],event['count'],True,ofile,skipFirst)
            print('\nSPOT:')
            if job=='SPOT' or job=='BOTH':
                processCW(event['cwdir'],event['count'],False,ofile,skipFirst)
    
            ############### Other #################
            print()
            if not processDB(event['dbdir'],event['count'],job,ofile,skipFirst):
                print('processDB failed, exiting...')
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parser for timings data from overhead.sh and overheadNS.sh')
    parser.add_argument('mrdir',action='store',help='full path to directory containing dirs named 1-10 under mr')
    parser.add_argument('cwdir',action='store',help='full path to directory containing dirs named 1-10 under cloudwatch')
    parser.add_argument('dbdir',action='store',help='full path to directory containing dirs named 1-10 under dynamodb')
    parser.add_argument('output_file',action='store',help='output file name')
    parser.add_argument('--process_MR_only',action='store_true',default=False,help='Run only the MR overhead processing')
    parser.add_argument('--process_NS_only',action='store_true',default=False,help='process the NS subdirectories (a non-SpotWrap job)')
    parser.add_argument('--process_spot_only',action='store_true',default=False,help='process the NS subdirectories (a non-SpotWrap job)')
    parser.add_argument('--skip_first',action='store_true',default=False,help='skip the first job (warmup)')
    parser.add_argument('--count',action='store',type=int,default=10,help='number of job dirs to process (default = 10)')
    args = parser.parse_args()
    if args.process_NS_only and args.process_spot_only:
        print('Error, process_NS_only and process_spot_only cannot both be set, use one or none and rerun')
        sys.exit(1)
    event = {}
    event['mrdir'] = args.mrdir
    event['cwdir'] = args.cwdir
    event['dbdir'] = args.dbdir
    event['output_fname'] = args.output_file
    event['count'] = args.count
    run = 'BOTH'
    if args.process_spot_only:
        run = 'SPOT'
    elif args.process_NS_only:
        run = 'NS'
    
    parseIt(event,run,args.skip_first,args.process_MR_only)

