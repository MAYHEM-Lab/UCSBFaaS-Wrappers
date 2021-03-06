import json,time,os,sys,argparse,statistics
from pprint import pprint
from enum import Enum

DEBUG = False
STATUS_LIST = [200.0,202.0,400.0]
BAD_LIST = ['c9fcf25c-998f-11e7-a275-41b194c286cd'] #extra reqs (assuming error logs)
def asint(s):
    try: return int(s), ''
    except ValueError: return sys.maxint, s

def check_dir(dir_key,event,job,jobcount):
    '''
    Check that the dirs and files exist (return True if so, else print error and return False)
    '''
    retn = False
    prefixes = []
    for n in range(1,jobcount+1):
        prefixes.append(str(n))
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

def processMicro(dirname,jobcount,ofile,skipFirst=False):
    fnames = [] 
    if DEBUG:
        print('processMicro')
    fnames = []
    ns_str = '/APIs'
    suffixes = ['C','T','F','D','S','B']

    #CJK here
    #n = 50
    #fnames.append('{}/{}{}/'.format(dirname,n,ns_str)) #dirnames
    for n in range(1,jobcount+1):
        if n > 1 or not skipFirst:
            fnames.append('{}/{}{}/'.format(dirname,n,ns_str)) #dirnames
    FILE_LIST = ["dbread","dbwrite","dbsetup","empty","emptySbig","pubsns","s3read","s3write","s3setup"]

    #for each file, collect job timings for each for jobcount runs
    for postfix in FILE_LIST:
        BIGTEST = False
        for suffix in suffixes:
            if postfix == "emptySbig": 
                if suffix != 'C':
                    continue
                outfname = '{}_{}.out'.format(ofile,postfix)
                BIGTEST = True
            else:
                outfname = '{}_{}{}.out'.format(ofile,postfix,suffix)
            with open(outfname,'w') as outf:
                count = 0
                tlist = []
                mlist = []
                reqs = []
                writtenTo = False
                for fname in fnames:
                    if not BIGTEST:
                        fname += '{}{}.log'.format(postfix,suffix)
                    else:
                        fname += '{}.log'.format(postfix)
                    if not os.path.isfile(fname):
                        continue
                    with open(fname,'r') as f:
                        for line in f:
                            if DEBUG:
                                print('processing: {}:{}'.format(fname,line))
                            line = line.strip()
                            if line.startswith('No streams'):
                                break
                            if line == '':
                                continue

                            strs = line.split(':')
                            if len(strs) != 4: #only process Record and GammaRay (S,D) values for now
                                continue
                            fn = strs[0]
                            req = strs[1]
                            if req in reqs or req in BAD_LIST:
                                #print('skipping req {}'.format(req))
                                continue #skip it if we've already see it
                            #Fn:reqID:duration_billed:mem_used	//Record
                            reqs.append(req)
                            tlist.append(float(strs[2]))
                            mlist.append(float(strs[3]))
                            count += 1
                            outf.write('{} {}\n'.format(float(strs[2]),float(strs[3])))
                            writtenTo = True
            if not writtenTo:
                os.remove(outfname)
                            
            if len(tlist) > jobcount:
                #print('{} longer list??? {} {}'.format(outfname,len(tlist),tlist))
                print('{} longer list??? {} {}'.format(outfname,len(tlist)))
            if len(tlist) > 1:
                print('{}{}:{}:{}:{}:{}:{}'.format(
                    postfix,suffix,len(tlist),
                    statistics.mean(tlist),statistics.stdev(tlist),
                    statistics.mean(mlist),statistics.stdev(mlist)
                ))
            else:
                print('{}{}:{}:{}:{}:{}:{}'.format(
                    postfix,suffix,len(tlist),0.0,0.0,0.0,0.0
                ))

def processMRNew2(dirname,jobcount,ofile):
    fnames = [] 
    if DEBUG:
        print('processMR overheadMR.sh output')
    suffixes = ['C','T','F','D','S','B']
    #for each config, a list of 50 values, each being the sum of avg per function
    #job1: avg(29maps) + avg(2 reducers) + 1coord + 1 dri 
    #job2: avg(29maps) + avg(2 reducers) + 1coord + 1 dri 
    avg = [[],[],[],[],[],[]]
    postfixes = ['coord.log','map.log','red.log','dri.log']
    
    #dirname/4/suffix/[coord,map,red].log
    #fnames.append('{}/{}/{}/red.log'.format(dirname,n,suffix)) #filenames
    for suffix in suffixes:
        print('processing suffix: {}'.format(suffix))
        outfname = '{}_mr{}.out'.format(ofile,suffix)
        outfname2 = '{}_map{}.out'.format(ofile,suffix)
        with open(outfname,'w') as outf, open(outfname2,'w') as outf2:
            for n in range(1,jobcount+1):
                reqs = []
                jobsum = 0
                jobmemsum = 0
                skip = False
                for fname in postfixes:
                    count = 0
                    tlist = []
                    mlist = []
                    fn = '{}/{}/{}/MRASYNC/{}'.format(dirname,n,suffix,fname)
                    print('processing {}'.format(fn))
                    if not os.path.isfile(fn):
                        print('file not found {}'.format(fn))
                        continue
                    with open(fn,'r') as f:
                        for line in f:
                            strs = line.split(':')
                            if len(strs) != 4: #only process Record and GammaRay (S,D) values for now
                                continue
                            fn = strs[0]
                            req = strs[1]
                            if req in reqs:
                                continue #skip it if we've already see it
                            #Fn:reqID:duration_billed:mem_used	//Record
                            reqs.append(req)
                            t = float(strs[2])
                            m = float(strs[3])
                            print('\tappending {} {}'.format(t,m))
                            tlist.append(t)
                            mlist.append(m)
                            count += 1
                            if fname == 'map.log':
                                outf2.write('{} {}\n'.format(t,m))
          
                    #print('adding {} {} {}'.format(suffix,statistics.mean(tlist),statistics.mean(mlist)))
                    if count != 0:
                        jobsum += statistics.mean(tlist)
                        jobmemsum += statistics.mean(mlist)
                    else:
                        skip = True
                   
                if not skip:
                    print('{} {} {}'.format(n,jobsum,jobmemsum))
                    outf.write('{} {}\n'.format(jobsum,jobmemsum))
                #else:
                    #print('skipping {} {} {}'.format(n,jobsum,jobmemsum))
                    
def processMRNew(dirname,jobcount,ofile,skipFirst=False,async=False):
    fnames = [] 
    if DEBUG:
        print('processMR overheadMR.sh output')
    suffixes = ['C','T','F','D','S','B']
    #for each config, a list of 50 values, each being the sum of avg per function
    #job1: avg(29maps) + avg(2 reducers) + 1coord + 1 dri 
    #job2: avg(29maps) + avg(2 reducers) + 1coord + 1 dri 
    avg = [[],[],[],[],[],[]]
    postfixes = ['coord.log','map.log','red.log']
    if async:
        postfixes.append('dri.log')
    
    #dirname/4/suffix/[coord,map,red].log
    #fnames.append('{}/{}/{}/red.log'.format(dirname,n,suffix)) #filenames
    for suffix in suffixes:
        jobsum = {}
        jobmemsum = {}
        for postfix in postfixes:
            outfname = '{}_{}{}.out'.format(ofile,postfix,suffix)
            if async:
                outfname += '_async'
            writtenTo = False
            count = 0
            tlist = []
            mlist = []
            reqs = []
            with open(outfname,'w') as outf:  #ex: out_coord.logS.out
                for n in range(1,jobcount+1):
                    if n > 1 or not skipFirst:
                        if async:
                            fname = '{}/{}/{}/MRASYNC/{}'.format(dirname,n,suffix,postfix)
                        else: 
                            fname = '{}/{}/{}/{}'.format(dirname,n,suffix,postfix)
                        if not os.path.isfile(fname):
                            if DEBUG:
                                print('file not found {}'.format(fname))
                            continue
                        with open(fname,'r') as f:
                            for line in f:
                                if DEBUG:
                                    print('processing: {}:{}'.format(fname,line))
                                line = line.strip()
                                if line.startswith('No streams'):
                                    break
                                if line == '':
                                    continue
            
                                strs = line.split(':')
                                if len(strs) != 4: #only process Record and GammaRay (S,D) values for now
                                    continue
                                fn = strs[0]
                                req = strs[1]
                                if req in reqs:
                                    continue #skip it if we've already see it
                                #Fn:reqID:duration_billed:mem_used	//Record
                                reqs.append(req)
                                t = float(strs[2])
                                m = float(strs[3])
                                nstr = str(n)
                                v = vm = 0
                                if nstr in jobsum:
                                    v = jobsum[nstr]
                                if nstr in jobmemsum:
                                    vm = jobmemsum[nstr]
                                v += t
                                vm += m
                                jobsum[str(n)] = v
                                jobmemsum[str(n)] = vm
                                tlist.append(t)
                                mlist.append(m)
                                count += 1
                                outf.write('{} {}\n'.format(float(strs[2]),float(strs[3])))
                                writtenTo = True
                if not writtenTo:
                    os.remove(outfname)
                    
                if len(tlist) > 1:
                    print('{}{}:{}:{}:{}:{}:{}'.format(
                        postfix,suffix,len(tlist),
                        statistics.mean(tlist),statistics.stdev(tlist),
                        statistics.mean(mlist),statistics.stdev(mlist)
                    ))
                else:
                    print('{}{}:{}:{}:{}:{}:{}'.format(
                        postfix,suffix,len(tlist),0.0,0.0,0.0,0.0
                    ))

        outfname = 'MR_{}.out_sum'.format(suffix)
        with open(outfname,'w') as outf:
            for n in range(1,jobcount+1):
                nstr = str(n)
                v = vm = 0
                if nstr in jobsum:
                    v = jobsum[nstr]
                if nstr in jobmemsum:
                    vm = jobmemsum[nstr]
                if v == 0 or vm == 0:
                    if v != vm:
                        print('v and vm do not match: {} {}'.format(v,vm))
                else:
                    outf.write('{} {}\n'.format(v,vm))
        jobsum = jobmemsum = {}
            
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
    if DEBUG:
        print('processCW: NSJob (1=spot,2=ns,3=fleece,4=gr) {}'.format(NSJob))
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
            fnames.append('{}/{}{}/'.format(dirname,n,ns_str)) #dirnames

    #for each file, collect job timings for each for jobcount runs
    for postfix in FILE_LIST:
        tlist = []
        swlist = []
        mlist = []
        reqs = []
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
                    if req in reqs:
                        continue #skip it if we've already see it
                    reqs.append(req)
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

def processMR(dirname,jobcount,NSJob,ofile,skipFirst=False):
    if DEBUG:
        print('processMR: NSJob (1=spot,2=ns,3=fleece,4=gr) {}'.format(NSJob))
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
                    if DEBUG:
                        print(fname,line)
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
    
def parseIt(ofile,event,job='both',skipFirst=False,mrOnly=False,microOnly=False):
    '''
    Parse the files output from an overhead job
    '''
    if not microOnly:
        if not check_dir('mrdir',event,job,event['count']) or not check_dir('cwdir',event,job,event['count']):
            print('check_dir failed, exiting...')
            sys.exit(1)

        print()
        if job=='NS' or job=='BOTH': #1=NS
            count,avg,stdev,mcount,dsize,keys = processMR(event['mrdir'],event['count'],1,ofile,skipFirst)
            print('NStotal:{},map_avg:{}:map_stdev:{}:map_count:{}:dsize:{}:keys:{}'.format(count,avg,stdev,mcount,dsize,keys))
        if job=='SPOT' or job=='BOTH': #2=Spot
            count,avg,stdev,mcount,dsize,keys = processMR(event['mrdir'],event['count'],2,ofile,skipFirst)
            print('SPOTtotal:{},map_avg:{}:map_stdev:{}:map_count:{}:dsize:{}:keys:{}'.format(count,avg,stdev,mcount,dsize,keys))
        mrdir = event['mrdir']
        mrdir = mrdir.replace('lambda-python/mr','gammaRay/apps/map-reduce')
    
        #3 = fleece
        count,avg,stdev,mcount,dsize,keys = processMR(mrdir,event['count'],3,ofile,skipFirst)
        print('Fleecetotal:{},map_avg:{}:map_stdev:{}:map_count:{}:dsize:{}:keys:{}'.format(count,avg,stdev,mcount,dsize,keys))
        #4 = GammaRay
        count,avg,stdev,mcount,dsize,keys = processMR(mrdir,event['count'],4,ofile,skipFirst)
        print('GammaRaytotal:{},map_avg:{}:map_stdev:{}:map_count:{}:dsize:{}:keys:{}'.format(count,avg,stdev,mcount,dsize,keys))

    if not mrOnly and not microOnly: 
        ############### Cloudwatch Log Summaries #################
        print('\nCloudwatch Log Data\n\tname,count,billed_avg,billed_stdev,inner_avg,inner_stdev,mem_avg,mem_stdev')
        print('NoSpot:')
        if job=='NS' or job=='BOTH':
            processCW(event['cwdir'],event['count'],1,ofile,skipFirst)
        print('\nSPOT:')
        if job=='SPOT' or job=='BOTH':
            processCW(event['cwdir'],event['count'],2,ofile,skipFirst)
        print('\nFLEECE:')
        processCW(event['cwdir'],event['count'],3,ofile,skipFirst)
        print('\nGammaRay:')
        processCW(event['cwdir'],event['count'],4,ofile,skipFirst)

    processMicro(event['cwdir'],event['count'],ofile,skipFirst)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parser for timings data from overhead.sh and overheadNS.sh')
    parser.add_argument('mrdir',action='store',help='full path to directory containing dirs named 1-10 under mr')
    parser.add_argument('cwdir',action='store',help='full path to directory containing dirs named 1-10 under cloudwatch')
    parser.add_argument('output_file_prefix',action='store',help='output file name prefix')
    parser.add_argument('--process_MRnew',action='store_true',default=False,help='Run only the MR overhead processing')
    parser.add_argument('--process_MRnewasync',action='store_true',default=False,help='Run only the MR overhead processing')
    parser.add_argument('--process_MR_only',action='store_true',default=False,help='Run only the MR overhead processing')
    parser.add_argument('--process_NS_only',action='store_true',default=False,help='process the NS subdirectories (a non-SpotWrap job)')
    parser.add_argument('--process_spot_only',action='store_true',default=False,help='process the NS subdirectories (a non-SpotWrap job)')
    parser.add_argument('--skip_first',action='store_true',default=False,help='skip the first job (warmup)')
    parser.add_argument('--micro_only',action='store_true',default=False,help='process only micro-benchmarks')
    parser.add_argument('--count',action='store',type=int,default=10,help='number of job dirs to process (default = 10)')
    args = parser.parse_args()
    if args.process_NS_only and args.process_spot_only:
        print('Error, process_NS_only and process_spot_only cannot both be set, use one or none and rerun')
        sys.exit(1)
    if args.process_MR_only and args.skip_MR:
        print('Error, process_MR_only and skip_MR cannot both be set, use one or none and rerun')
        sys.exit(1)
    event = {}
    event['mrdir'] = args.mrdir
    event['cwdir'] = args.cwdir
    event['count'] = args.count
    run = 'BOTH'
    if args.process_spot_only:
        run = 'SPOT'
    elif args.process_NS_only:
        run = 'NS'


    processMRNew2(args.cwdir,args.count,args.output_file_prefix)
    #if args.process_MRnewasync:
        #processMRNew(args.cwdir,args.count,args.output_file_prefix,False,True)
    #elif args.process_MRnew:
        #processMRNew(args.cwdir,args.count,args.output_file_prefix)
    #else:
        #parseIt(args.output_file_prefix,event,run,args.skip_first,args.process_MR_only,args.micro_only)

