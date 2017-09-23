'''
 make configuration files for GammaRay and SpotWrap
 Author: Chandra Krintz
 License and Copyright in ../LICENSE
'''
import sys,time,glob,subprocess,argparse,os,tempfile,shutil,random,json

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='make python3 configs for setupApps.py')
    parser.add_argument('configDir',action='store',default='configs',help='directory into which the config files will go')
    parser.add_argument('--swbkt',action='store',default='cjktestbkt',help='bucket for spotwrap libs')
    parser.add_argument('--swbkteast',action='store',default='cjktestbkteast',help='bucket for spotwrap libs')
    parser.add_argument('botocore_dir',action='store',help='full path to patched botocore directory')
    parser.add_argument('fleece_dir',action='store',help='full path to patched fleece directory')
    parser.add_argument('other_libs_dir',action='store',help='full path to directory with other libraries in it')
    parser.add_argument('--Bversion',action='store',default=None,help='full path to directory with fleece_lite version')
    args = parser.parse_args()
    
    fleece_dir = args.fleece_dir
    botocore_dir = args.botocore_dir
    other_libs_dir = args.other_libs_dir
    if not os.path.isdir(args.configDir):
        print('Error, filename passed in for configs must be an existing directory (make sure its empty)')
        sys.exit(1)
    if not os.path.isdir(fleece_dir) or not fleece_dir.endswith('fleece'):
        print('Error, filename passed in for fleece must be an existing directory (...site-packages/fleece): {}'.format(fleece_dir))
        sys.exit(1)
    if args.Bversion:
        if not os.path.isdir(args.Bversion) or not args.Bversion.endswith('fleece'):
            print('Error, filename passed in for fleece (Bversion) must be an existing directory (...site-packages/fleece): {}'.format(fleece_dir))
            sys.exit(1)
    if not os.path.isdir(botocore_dir) or not botocore_dir.endswith('botocore'):
        print('Error, filename passed in for botocore must be an existing directory (...site-packages/botocore): {}'.format(botocore_dir))
        sys.exit(1)
    if not os.path.isdir(other_libs_dir) or not other_libs_dir.endswith('site-packages'):
        print('Error, filename passed in for botocore must be an existing directory (...site-packages): {}'.format(other_libs_dir))
        sys.exit(1)

    suffixes = [
        'C', #clean/nothing default Lambda
        'T', #tracing turned on
        'F', #tracing + fleece turned on
        'S', #static GammaRay (original spotwrap)
        'D', #dynamic GammaRay (spotwrap reimplemented using fleece)
        'B', #both tracing and dynamic GammaRay for writes only
    ]
    apps = {
        'DBSyncPy':'apps/DBSync.py',
        'ImageProcPy':'apps/imageProc.py',
        'DBModPy':'apps/dbMod.py',
        'S3ModPy':'apps/s3Mod.py',
        'SNSPy':'apps/sns.py',
        'FnInvokerPy':'apps/FnInvoker.py',
        'mapper':'apps/map-reduce/mapper.py',
        'reducer':'apps/map-reduce/reducer.py',
        'driver':'apps/map-reduce/driver.py',
        'reducerCoordinator':'apps/map-reduce/reducerCoordinator.py',
        'UpdateWebsite':'apps/FnInvoker.py',
        'dbread':'micro-benchmarks/dbread.py',
        'dbsetup':'micro-benchmarks/dbsetup.py',
        'dbwrite':'micro-benchmarks/dbwrite.py',
        'empty':'micro-benchmarks/empty.py',
        'pubsns':'micro-benchmarks/pubsns.py',
        's3read':'micro-benchmarks/s3read.py',
        's3setup':'micro-benchmarks/s3setup.py',
        's3write':'micro-benchmarks/s3write.py',
    }
    #specify the bucket and prefix (folder) in bucket to use to trigger function lambda_name
    #bucket names must be unique and identifiable (for run type: C,T,F,S,D,B)
    if 'FNI_TRIGGERBKTF' not in os.environ \
        or 'FNI_TRIGGERBKTC' not in os.environ \
        or 'FNI_TRIGGERBKTD' not in os.environ \
        or 'FNI_TRIGGERBKTS' not in os.environ \
        or 'FNI_TRIGGERBKTT' not in os.environ \
        or 'FNI_TRIGGERBKTB' not in os.environ:
        print('Error: you must set FNI_TRIGGERBKTX env variables for s3 bucket names  (X=FCDSTB)')
        sys.exit(1)
    if 'IMG_TRIGGERBKTF' not in os.environ \
        or 'IMG_TRIGGERBKTC' not in os.environ \
        or 'IMG_TRIGGERBKTD' not in os.environ \
        or 'IMG_TRIGGERBKTS' not in os.environ \
        or 'IMG_TRIGGERBKTT' not in os.environ \
        or 'IMG_TRIGGERBKTB' not in os.environ:
        print('Error: you must set IMG_TRIGGERBKTX env variables for s3 bucket names  (X=FCDSTB)')
        sys.exit(1)
    if 'MR_TRIGGERBKTF' not in os.environ \
        or 'MR_TRIGGERBKTC' not in os.environ \
        or 'MR_TRIGGERBKTD' not in os.environ \
        or 'MR_TRIGGERBKTS' not in os.environ \
        or 'MR_TRIGGERBKTT' not in os.environ \
        or 'MR_TRIGGERBKTB' not in os.environ:
        print('Error: you must set MR_TRIGGERBKTX env variables for s3 bucket names  (X=FCDSTB)')
        sys.exit(1)

    triggerBuckets = {  #lambda_name:bucket:bucket_prefix
        ('FnInvokerPyC',os.environ['FNI_TRIGGERBKTC'],'prefC'),
        ('FnInvokerPyT',os.environ['FNI_TRIGGERBKTT'],'prefT'),
        ('FnInvokerPyF',os.environ['FNI_TRIGGERBKTF'],'prefF'),
        ('FnInvokerPyS',os.environ['FNI_TRIGGERBKTS'],'prefS'),
        ('FnInvokerPyD',os.environ['FNI_TRIGGERBKTD'],'prefD'),
        ('FnInvokerPyB',os.environ['FNI_TRIGGERBKTB'],'prefB'),
        ('ImageProcPyC',os.environ['IMG_TRIGGERBKTC'],'imageProc'),
        ('ImageProcPyT',os.environ['IMG_TRIGGERBKTT'],'imageProc'),
        ('ImageProcPyF',os.environ['IMG_TRIGGERBKTF'],'imageProc'),
        ('ImageProcPyS',os.environ['IMG_TRIGGERBKTS'],'imageProc'),
        ('ImageProcPyD',os.environ['IMG_TRIGGERBKTD'],'imageProc'),
        ('ImageProcPyB',os.environ['IMG_TRIGGERBKTB'],'imageProc'),
        ('reducerCoordinatorC',os.environ['MR_TRIGGERBKTC'],'job8000'),
        ('reducerCoordinatorT',os.environ['MR_TRIGGERBKTT'],'job8000'),
        ('reducerCoordinatorF',os.environ['MR_TRIGGERBKTF'],'job8000'),
        ('reducerCoordinatorS',os.environ['MR_TRIGGERBKTS'],'job8000'),
        ('reducerCoordinatorD',os.environ['MR_TRIGGERBKTD'],'job8000'),
        ('reducerCoordinatorB',os.environ['MR_TRIGGERBKTB'],'job8000')
    }

    #specify the DynamoDB table stream that triggers lambda function lambda_name
    triggerTables = { #lambda_name,table_name 
        ('DBSyncPy','imageLabels'),
        ('UpdateWebsite','eastSyncTable'),
    }

    #now create a config for all of the lambda's in the west region
    regs = [('us-west-2','',args.swbkt),('us-east-1','East',args.swbkteast)]
    for regtuple in regs:
        reg = regtuple[0]
        end = regtuple[1]
        swbkt = regtuple[2]
        for suffix in suffixes:
            fname = '{}/config{}{}.json'.format(args.configDir,end,suffix)
            jsonf = {}
            fun = []
            for key in apps:
                entry = apps[key]    

                #add app names two these two entries for lambdas you want to create in east only (UpdateWebsite)
                if reg == 'us-east-1' and (key != 'UpdateWebsite'):
                    continue
                if reg == 'us-west-2' and (key == 'UpdateWebsite'):
                    continue

                if not os.path.isfile(entry):
                    print('Error, script in apps list does not exist: {}'.format(entry))
                    sys.exit(1)
                k = entry.rfind("/")
                idx = entry.find(".py")
                assert idx > 0
                pyfile = entry[k+1:idx]
                files_and_dirs = [
                    '{}'.format(entry)
                ]

                if args.Bversion and suffix == 'B':
                    final_fleece_dir = args.Bversion
                else:
                    final_fleece_dir = fleece_dir

                #append other libs and python files here via files_and_dirs.append
                #adding them to the local/gammaray virtualenv (other_libs_dir) is easiest 
                if key == 'driver' or key == 'reducerCoordinator':
                    files_and_dirs.append("apps/map-reduce/lambdautils.py")

                if key == 'FnInvokerPy' or key == "ImageProcPy" or key == 'UpdateWebsite' or key == 'DBModPy' or key == 'DBSyncPy':
                    #requests is a fleece dependency
                    if suffix != 'F' and suffix != 'D' and suffix != 'B': #don't add them twice (will be added below for F and D and B)
                        files_and_dirs.append("{}/requests".format(other_libs_dir))
                        files_and_dirs.append("{}/urllib3".format(other_libs_dir))
                        files_and_dirs.append("{}/chardet".format(other_libs_dir))
                        files_and_dirs.append("{}/certifi".format(other_libs_dir))
                        files_and_dirs.append("{}/idna".format(other_libs_dir))
                if suffix == 'F' or suffix == 'D' or suffix == 'B':
                    files_and_dirs.append(final_fleece_dir)
                    files_and_dirs.append("{}/requests".format(other_libs_dir))
                    files_and_dirs.append("{}/urllib3".format(other_libs_dir))
                    files_and_dirs.append("{}/chardet".format(other_libs_dir))
                    files_and_dirs.append("{}/certifi".format(other_libs_dir))
                    files_and_dirs.append("{}/idna".format(other_libs_dir))
                    files_and_dirs.append("{}/structlog".format(other_libs_dir))
                    files_and_dirs.append("{}/wrapt".format(other_libs_dir))
                
                mem = 128
                if 'mapper' in key or 'reducer' in key:
                    mem = 1536
                name = "{}{}".format(key,suffix)
                app = {
                    "name": name,
                    "lambdaMemory": mem,
                    "handler": "{}.handler".format(pyfile),
                    "zip": "package.zip",
                    "files_and_dirs": files_and_dirs,
                    "patched_botocore_dir": botocore_dir,
                    "s3bucket": swbkt
                }
                for needsBucket in triggerBuckets:
                    fn = needsBucket[0] 
                    bkt = needsBucket[1]
                    prefix = needsBucket[2]
                    if name == fn: 
                        app["permission"]= bkt
                        app["job_id"]= prefix

                for needsTable in triggerTables:
                    fn = needsTable[0]
                    v = needsTable[1]
                    if name == fn: 
                        app["table"]= v
                        
                fun.append(app)

            #write out the file in json, if any functions were added to fun
            if fun != []:
                jsonf = {
                    "region":reg,
                    "functions":fun
                }
                with open(fname, 'w') as f :
                    json.dump(jsonf, f, indent=4)

         
