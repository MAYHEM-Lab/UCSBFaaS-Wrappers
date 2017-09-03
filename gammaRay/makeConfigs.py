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
    args = parser.parse_args()
    
    suffixes = [
        'C', #clean/nothing default Lambda
        'T', #tracing turned on
        'F', #tracing + fleece turned on
        'S', #static GammaRay (original spotwrap)
        'D', #dynamic GammaRay (spotwrap reimplemented using fleece)
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
    }
    #specify the bucket and prefix (folder) in bucket to use to trigger function lambda_name
    #bucket names must be unique and identifiable (for run type: C,T,F,S,D)
    triggerBuckets = {  #lambda_name:bucket:bucket_prefix
        ('ImageProcPyC','image-proc-c','imageProc'),
        ('ImageProcPyT','image-proc-t','imageProc'),
        ('ImageProcPyF','image-proc-f','imageProc'),
        ('ImageProcPyS','image-proc-s','imageProc'),
        ('ImageProcPyD','image-proc-d','imageProc'),
        ('reducerCoordinatorC','spot-mr-bkt-ns','job8000'),
        ('reducerCoordinatorT','spot-mr-bkt-t','job8000'),
        ('reducerCoordinatorF','spot-mr-bkt-t2','job8000'),
        ('reducerCoordinatorS','spot-mr-bkt','job8000'),
        ('reducerCoordinatorD','spot-mr-bkt-gr','job8000')
    }

    #specify the DynamoDB table stream that triggers lambda function lambda_name
    triggerTables = { #lambda_name,table_name 
        ('DBSyncPy','imageLabels'),
        ('UpdateWebsite','eastSyncTable'),
    }
    if not os.path.isdir(args.configDir):
        print('Error, filename passed in must be an existing directory (make sure its empty)')
        sys.exit(1)

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
                if key == 'driver' or key == 'reducerCoordinator':
                    files_and_dirs.append("apps/map-reduce/lambdautils.py")
                if suffix == 'F' or suffix == 'G':
                    files_and_dirs.append("apps/venv/lib/python3.6/site-packages/fleece")
                    files_and_dirs.append("apps/venv/lib/python3.6/site-packages/requests")
                    files_and_dirs.append("apps/venv/lib/python3.6/site-packages/urllib3")
                    files_and_dirs.append("apps/venv/lib/python3.6/site-packages/chardet")
                    files_and_dirs.append("apps/venv/lib/python3.6/site-packages/certifi")
                    files_and_dirs.append("apps/venv/lib/python3.6/site-packages/idna")
                    files_and_dirs.append("apps/venv/lib/python3.6/site-packages/structlog")
                    files_and_dirs.append("apps/venv/lib/python3.6/site-packages/wrapt")
                
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
                    "patched_botocore_dir": "venv/lib/python3.6/site-packages/botocore",
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

         
