import json,time,os,sys,argparse,statistics
from pprint import pprint
from enum import Enum

DEBUG = False
def parseIt(dirname,ofile,jobcount,subdir):
    fnames = [] 
    if DEBUG:
        print('parseIt')
    fnames = []
    suffixes = ['C','T','F','D','S','B']

    for n in range(1,jobcount+1):
        fnames.append('{}/{}/APP/{}'.format(dirname,n,subdir)) #dirnames
    if subdir == 'IMGPROC':
        FILE_LIST = ["DBSyncPy","ImageProcPy","UpdateWebsite"]
    elif subdir == 'WEBAPP':
        FILE_LIST = ["DBModPy","FnInvokerPy","SNSPy","S3ModPy"]

    #for each file, collect job timings for each for jobcount runs
    for postfix in FILE_LIST:
        for suffix in suffixes:
            outfname = '{}_{}_{}.out'.format(ofile,postfix,suffix)
            with open(outfname,'w') as outf:
                count = 0
                tlist = []
                mlist = []
                reqs = []
                writtenTo = False
                for pref in fnames:
                    fname = '{}/{}/{}{}.log'.format(pref,suffix,postfix,suffix)
                    if DEBUG:
                        print('fname: {}, ofile:{}'.format(fname,outfname))
                    if not os.path.isfile(fname):
                        continue
                    with open(fname,'r') as f:
                        for line in f:
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
                            tlist.append(float(strs[2]))
                            mlist.append(float(strs[3]))
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parser for timings data from imageProc.sh and webapp.sh')
    parser.add_argument('datadir',action='store',help='full path to directory containing dirs named 1-...')
    parser.add_argument('output_file_prefix',action='store',help='output file name prefix')
    parser.add_argument('--count',action='store',type=int,default=10,help='number of job dirs to process (default = 10)')
    args = parser.parse_args()
    datadir = args.datadir
    if not os.path.isdir(datadir):
        print('Error:  {} must be a directory'.format(datadir))
        sys.exit(1)
    print('IMGPROC')
    parseIt(datadir,args.output_file_prefix,args.count,'IMGPROC')
    print('\nWEBAPP')
    parseIt(datadir,args.output_file_prefix,args.count,'WEBAPP')

