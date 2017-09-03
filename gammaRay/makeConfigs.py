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
    args = parser.parse_args()
    
    suffixes = ['C', #clean/nothing default Lambda
        'T', #tracing turned on
        'F', #tracing + fleece turned on
        'S', #static GammaRay (original spotwrap)
        'D', #dynamid GammaRay (spotwrap reimplemented using fleece)
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
    }
    if not os.path.isdir(args.configDir):
        print('Error, filename passed in must be an existing directory (make sure its empty)')
        sys.exit(1)

    #now create a config for all of the lambda's in the west region
    reg = 'us-west-2'
    swbkt = args.swbkt
    for suffix in suffixes:
        fname = '{}/config{}.json'.format(args.configDir,suffix)
        jsonf = {}
        fun = []
        for key in apps:
            entry = apps[key]    
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
            if 'driver' in key or 'reducerCoordinator' in key:
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
            app = {
                "name": "{}{}".format(key,suffix),
                "lambdaMemory": mem,
                "handler": "{}.handler".format(pyfile),
                "zip": "package.zip",
                "files_and_dirs": files_and_dirs,
                "patched_botocore_dir": "venv/lib/python3.6/site-packages/botocore",
                "s3bucket": swbkt
            }
            fun.append(app)
        jsonf = {
            "region":reg,
            "functions":fun
        }
        with open(fname, 'w') as f :
            json.dump(jsonf, f, indent=4)
         
