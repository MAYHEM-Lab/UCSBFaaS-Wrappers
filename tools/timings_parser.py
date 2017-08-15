import json,time,os,sys,argparse,statistics
from pprint import pprint
from enum import Enum

DEBUG = False
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
        
def processCW(dirname,NSJob,ofile,skipFirst=False):
    pass
def processDB(dirname,NSJob,ofile,skipFirst=False):
    pass
def processMR(dirname,NSJob,ofile,skipFirst=False):
    fnames = []
    if NSJob:
        if not skipFirst:
            fnames.append('{}/1/NS/overhead.out'.format(dirname))
        fnames.append('{}/2/NS/overhead.out'.format(dirname))
        fnames.append('{}/3/NS/overhead.out'.format(dirname))
        fnames.append('{}/4/NS/overhead.out'.format(dirname))
        fnames.append('{}/5/NS/overhead.out'.format(dirname))
        fnames.append('{}/6/NS/overhead.out'.format(dirname))
        fnames.append('{}/7/NS/overhead.out'.format(dirname))
        fnames.append('{}/8/NS/overhead.out'.format(dirname))
        fnames.append('{}/9/NS/overhead.out'.format(dirname))
        fnames.append('{}/10/NS/overhead.out'.format(dirname))
    else:
        if not skipFirst:
            fnames.append('{}/1/overhead.out'.format(dirname))
        fnames.append('{}/2/overhead.out'.format(dirname))
        fnames.append('{}/3/overhead.out'.format(dirname))
        fnames.append('{}/4/overhead.out'.format(dirname))
        fnames.append('{}/5/overhead.out'.format(dirname))
        fnames.append('{}/6/overhead.out'.format(dirname))
        fnames.append('{}/7/overhead.out'.format(dirname))
        fnames.append('{}/8/overhead.out'.format(dirname))
        fnames.append('{}/9/overhead.out'.format(dirname))
        fnames.append('{}/10/overhead.out'.format(dirname))
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
            sys.exit(1)
        ids += 1
        with open(fname,'r') as f:
            for line in f:
                line = line.strip()
                if DEBUG:
                    print('{}:{}'.format(fname,line))
                if line.startswith('Dataset size'):
                    sline = line.split(' ')
                    dsize = float(sline[2].strip(','))
                    keycount = int(sline[4].strip(','))
                if line.startswith('Num. of Mappers'):
                    sline = line.split(' ')
                    mappers = int(sline[6])
                if line.startswith('mapper output'):
                    sline = line.split(' ')
                    if NSJob:
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
    
def parseIt(event,job='both',skipFirst=False):
    '''
    Parse the files output from an overhead job
    '''
    if not check_dir('mrdir',event,job) or not check_dir('dbdir',event,job) or not check_dir('cwdir',event,job):
        print('check_dir failed, exiting...')
        sys.exit(1)

    if 'output_fname' not in event:
        print('no output file name specified, exiting...')
        sys.exit(1)

    print("JOB: {}".format(job))
    with open(event['output_fname'],'w') as ofile: #first to open so overwrite and start fresh
        if job=='NS' or job=='BOTH':
            count,avg,stdev,mcount,dsize,keys = processMR(event['mrdir'],True,ofile,skipFirst)
            print('NStotal:{},map_avg:{}:map_stdev:{}:map_count:{}:dsize:{}:keys:{}'.format(count,avg,stdev,mcount,dsize,keys))
        if job=='SPOT' or job=='BOTH':
            count,avg,stdev,mcount,dsize,keys = processMR(event['mrdir'],False,ofile,skipFirst)
            print('SPOTtotal:{},map_avg:{}:map_stdev:{}:map_count:{}:dsize:{}:keys:{}'.format(count,avg,stdev,mcount,dsize,keys))
        if not processCW(event['cwdir'],job,ofile):
            print('processCW failed, exiting...')
        if not processDB(event['dbdir'],job,ofile):
            print('processDB failed, exiting...')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parser for timings data from overhead.sh and overheadNS.sh')
    parser.add_argument('mrdir',action='store',help='full path to directory containing dirs named 1-10 under mr')
    parser.add_argument('cwdir',action='store',help='full path to directory containing dirs named 1-10 under cloudwatch')
    parser.add_argument('dbdir',action='store',help='full path to directory containing dirs named 1-10 under dynamodb')
    parser.add_argument('output_file',action='store',help='output file name')
    parser.add_argument('--process_NS_only',action='store_true',default=False,help='process the NS subdirectories (a non-SpotWrap job)')
    parser.add_argument('--process_spot_only',action='store_true',default=False,help='process the NS subdirectories (a non-SpotWrap job)')
    parser.add_argument('--skip_first',action='store_true',default=False,help='skip the first job (warmup)')
    args = parser.parse_args()
    if args.process_NS_only and args.process_spot_only:
        print('Error, process_NS_only and process_spot_only cannot both be set, use one or none and rerun')
        sys.exit(1)
    event = {}
    event['mrdir'] = args.mrdir
    event['cwdir'] = args.cwdir
    event['dbdir'] = args.dbdir
    event['output_fname'] = args.output_file
    run = 'BOTH'
    if args.process_spot_only:
        run = 'SPOT'
    elif args.process_NS_only:
        run = 'NS'
    
    parseIt(event,run,args.skip_first)

