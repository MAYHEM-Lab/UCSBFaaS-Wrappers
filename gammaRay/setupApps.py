'''
 Driver to deploy SpotWrapped Apps
 Author: Chandra Krintz
 License and Copyright in ../LICENSE
    #from fleece.xray import (monkey_patch_botocore_for_xray, monkey_patch_requests_for_xray, trace_xray_subsegment)
    #monkey_patch_botocore_for_xray()
    #monkey_patch_requests_for_xray()
'''
import boto3,botocore,json
import sys,time,glob,subprocess,argparse,os,tempfile,shutil,random
import lambdautils

### UTILS ####
def zipLambda(zipname,ziplist,update=False):
    ''' Create a zip file, and add each file and (directory recursively) to it.

        Names in ziplist can be files or directories.
        Non-directories will be stored together in top level directory.
        e.g.: xxx.py /var/log/yyy.py results in xxx.py and yyy.py in basedir when unzipped
        Directories in ziplist will be stored at top level directory 
        and recursively include all files underneath them (deep copy)
        e.g.: /var/log/ddd ./bbb results in ddd and bbb directories in basedir 
        (with contents) when unzipped.
	If entry in zip list contains the name site-packages (e.g. venv/lib/xxx/site-packages), 
        the contents of this directory will be in the basedir when unzipped.
	The ziplist should not include any boto directories (they are already 
	available in AWS Lambda).

	See also zappa blog.zappa.io
    '''
    here = os.path.abspath(os.path.dirname(__file__))
    zipname = here+'/'+zipname
    if os.path.exists(zipname): #remove the zip file first
        if not update: #save time by only updating differences for existing zip
            os.remove(zipname)

    for fname in ziplist:
        if os.path.isfile(fname) or os.path.isdir(fname): #file exists
            dirname = os.path.dirname(fname)
            if fname.endswith('site-packages'):
                dirname = fname
                os.chdir(dirname) #go to dir to place file at top level
                subprocess.call(['zip', '-9', '-u', '-r','--exclude=*.pyc', zipname] +glob.glob('*'))
            else:
                fname = os.path.basename(fname)
                if dirname != '':
                    os.chdir(dirname) #go to dir to place file at top level
                subprocess.call(['zip', '-9', '-u', '-r','--exclude=*.pyc', zipname, fname])
            os.chdir(here)
        else:
            print('Error: file not found: {}'.format(fname))
            print('Please fix your config file and rerun')
            sys.exit(1)
    return zipname

def processLambda(config_fname, profile, noWrap=False, update=False, deleteThem=False, noBotocore=False, spotTableRegion='us-west-2', spotTableName='gammaRays',saveBucket=False,tracing=False,useGammaRay=False, useFleece=False):
    # Config
    try:
        config = json.loads(open(config_fname, 'r').read())
    except:
        print('Error loading json file, please fix formatting problems (commas?), and retry...({})'.format(config_fname))
        sys.exit(1)
    region = config['region']
    fns = config['functions']

    if profile:
        boto3.setup_default_session(profile_name=profile)
    config = botocore.client.Config(connect_timeout=50, read_timeout=100)
    lambda_client = boto3.client('lambda',config=config,region_name=region)
    s3 = None
    s3_client = None
    if not noBotocore:
        s3 = boto3.resource('s3')
        config = botocore.client.Config(connect_timeout=50, read_timeout=200)
    s3_client = boto3.client('s3',config=config,region_name=region) #used to set trigger
    gammawraptemplate = 'GammaRay.py.template'
    gammawrapfile = 'GammaRay.py'
    spotwraptemplate = 'SpotWrap.py.template'
    spotwrapfile = 'SpotWrap.py'

    #Create the lambda functions
    for fn in fns:
        name = fn['name']
        if deleteThem: #don't do anything more if we are deleting
            try:
                l_fn = lambdautils.LambdaManager(lambda_client, region, None, name, None)
                l_fn.delete_function()
                print('setupApps: {} deleted'.format(name))
            except Exception as e:
                stre = str(e)
                if 'ResourceNotFoundException' not in stre:
                    print('EXCEPTION in lambda delete: {}'.format(e))
            try:
                if not saveBucket and 'permission' in fn:
                    bkt = fn['permission']
                    print('setupApps: bucket contents for {} deleted'.format(bkt))
                    lambdautils.LambdaManager.deleteBucketContents(s3,bkt)
            except:
                pass
            try:
                lambdautils.LambdaManager.cleanup_logs(name)
            except:
                pass
            continue #get the next function to delete

        #else process the rest and create the Lambdas
        lambda_memory = fn['lambdaMemory']
        ziplist = fn['files_and_dirs']
        zipfile = fn['zip']
        handler = fn['handler'] #must be of the form filename.handlername
        periods = handler.count('.')
        peridx = handler.find('.')
        if periods != 1 or peridx == 0:
            print('Error, the handler entry for {} must be of the form filename.handlername.  Please fix and rerun.'.format(name))
            sys.exit(1)

        tmp_dir = None
        if useGammaRay: #inject GammaWrap support (produce functions with and without GammaWrap support
            if not os.path.isfile(gammawraptemplate):
                print('Error, {} Not Found!  To inject GammaWrap support, rerun this program in the same directory as GammaWrap.py. Not injecting GammaWrap support...'.format(gammawraptemplate))
                sys.exit(1)

            else: #inject GammaWrap support (produce functions with GammaWrap support)
                tmp_dir = tempfile.mkdtemp() 
                target = '{}/{}'.format(tmp_dir,gammawrapfile)
                print('target: {}'.format(target))
                shutil.copyfile(gammawraptemplate,target) #copy the template into temp dir
                ziplist.append(target) #add temp dir and file to the zip list so we include it

                #next update the template to call the user's handler
                orig_file = handler[:peridx] #filename containing original handler
                orig_handler = handler
                handler = 'GammaRay.handleRequest'
                print('orig: {}:{} -- {}'.format(orig_file,orig_handler,handler))

                # Read in the file, replace the string, and write it out
                with open(target, 'r') as f :
                    filedata = f.read()
                filedata = filedata.replace('import GammaRayTemplate', 'import {}'.format(orig_file))
                filedata = filedata.replace('GammaRayTemplate.handler', orig_handler)
                filedata = filedata.replace('ZZZZ', spotTableRegion)
                filedata = filedata.replace('QQQQ', spotTableName)
                # Write the file out 
                with open(target, 'w') as f:
                    f.write(filedata)
   
                print('setupApps: GammaRay support inserted')

        if useFleece: #inject Fleece 
            tmp_dir = tempfile.mkdtemp() 
            fname2find = '{}.py'.format(handler[:peridx]) #filename containing original handler
            found = False
            for fnameInOriginalLoc in ziplist:
                if fnameInOriginalLoc.endswith(fname2find):
                    found = True
                    break
            if not found:
                print('Error, {} not found in ziplist {}'.format(fname2find,ziplist))
                sys.exit(1)
            ziplist.remove(fnameInOriginalLoc) #remove from ziplist
            target = '{}/{}'.format(tmp_dir,fname2find) #same file only in tmp_dir
            ziplist.append(target) #add file in new location to ziplist
            print('target: {}'.format(target))

            #next update the code in target to include fleece
            with open(fnameInOriginalLoc, 'r') as f :
                filedata = f.read()
            # Write the file out 
            with open(target, 'w') as f:
                f.write('from fleece.xray import (monkey_patch_botocore_for_xray, monkey_patch_requests_for_xray, trace_xray_subsegment)')
                f.write('monkey_patch_botocore_for_xray()')
                f.write('monkey_patch_requests_for_xray()')
                f.write(filedata)
  
            print('setupApps: Fleece support inserted')

        elif not noWrap: #do not useGammaRay, no not use Fleece, so use spotwrap (not noWrap) or nothing:
            ''' Process the patched botocore file (place in S3 for SpotWrap.py to download)''' 
            botozipdir = None
            zipbase = 'botocore_patched.zip'
            zipname = '/tmp/{}'.format(zipbase) #this much match same in SpotWrap.py.template

            if 'patched_botocore_dir' not in fn or fn['patched_botocore_dir'] == '': #no patch dir specified
                print('patched_botocore_dir not set in configuration file. To inject SpotWrap support, set this value and rerun this program. Not injecting SpotWrap support...')
                noWrap = True
            else:
                if 'patched_botocore_dir' in fn:
                    botozipdir = fn['patched_botocore_dir']
                    if not os.path.isdir(botozipdir):
                        noWrap = True
      
            s3bkt = 'spotbucket'
            if 's3bucket' not in fn or fn['s3bucket'] == '': #double check that this exists
                print('No s3 bucket name (s3bucket) found in configuration file. Not injecting SpotWrap support...')
                noWrap = True
            else: #s3bucket is set, check that it is a valid S3 bucket
                s3bkt = fn['s3bucket']
                if not noBotocore:
                    noBotocore = True
                    if lambdautils.LambdaManager.S3BktExists(s3,s3bkt,region):
                        #zip up the patched botocore directory and place in S3
                        if not botozipdir: #sanity check
                            print('setupApps Error:  botozipdir is None unexpectedly here')
                            sys.exit(1)
                        here = os.path.abspath(os.path.dirname(__file__))
                        dirname = os.path.dirname(botozipdir)
                        fname = os.path.basename(botozipdir)
                        if dirname != '':
                            os.chdir(dirname) #go to dir to place file at top level
                        if os.path.exists(zipname): #remove the zip file first
                            os.remove(zipname)
                        subprocess.call(['zip', '-9', '-u', '-r','--exclude=*.pyc', zipname, fname])
                        try:
                            lambdautils.LambdaManager.copyToS3(s3,s3bkt,zipname)
                        except Exception as e:
                            print('setupApps: S3 error on zip file storage:\n{}'.format(e))
                            sys.exit(1)
                        os.chdir(here)
                 
            ''' Inject SpotWrap Support '''
            #first check that SpotWrap.py is in the current working directory
            if not os.path.isfile(spotwraptemplate):
                print('Error, {} Not Found!  To inject SpotWrap support, rerun this program in the same directory as SpotWrap.py. Not injecting SpotWrap support...'.format(spotwraptemplate))
            else: #inject SpotWrap support
                #first remove SpotWrap.py so we don't confuse things, if added by mistake
                todel = []
                for fname in ziplist:
                    #if fname.endswith(spotwrapfile) or fname.endswith('botocore'):
                    if fname.find('boto') != -1:
                        print('Found boto in the list, AWS Lambda installs boto for you, please remove to reduce the size of your zip, and rerun: {}'.format(fname))
                        sys.exit(1)
                    if fname.endswith(spotwrapfile):
                        todel.append(fname) #can't remove while iterating...
                for fname in todel:
                    ziplist.remove(fname)
                tmp_dir = tempfile.mkdtemp() 
                target = '{}/{}'.format(tmp_dir,spotwrapfile)
                shutil.copyfile(spotwraptemplate,target) #copy the template into temp dir
                ziplist.append(target) #add temp dir and file to the zip list so we include it
   
                #next update the template to call the user's handler
                orig_file = handler[:peridx] #filename containing original handler
                orig_handler = handler
                handler = 'SpotWrap.handleRequest'
                # Read in the file, replace the string, and write it out
                with open(target, 'r') as f :
                    filedata = f.read()
                filedata = filedata.replace('import SpotTemplate', 'import {}'.format(orig_file))
                filedata = filedata.replace('SpotTemplate.handler', orig_handler)
                filedata = filedata.replace('XXXX', s3bkt)
                filedata = filedata.replace('YYYY', zipbase)
                filedata = filedata.replace('ZZZZ', spotTableRegion)
                filedata = filedata.replace('QQQQ', spotTableName)
                # Write the file out 
                with open(target, 'w') as f:
                    f.write(filedata)
       
                print('setupApps: SpotWrap support inserted')

        else: #no GammaWrap and not noSpotWrap and no Fleece (clean deploy)
            print('setupApps: no GammaWrap and no Fleece and no SpotWrap support inserted')

        l_zip = zipLambda(zipfile,ziplist,update)
        if tmp_dir:
            shutil.rmtree(tmp_dir)

        print('handler: {}'.format(handler))
        #create lambdas
        l_fn = lambdautils.LambdaManager(lambda_client, region, l_zip, name, handler,tracing,lambda_memory)
        l_fn.update_code_or_create_on_noexist()
        if 'permission' in fn:
            job_bucket = fn['permission']
            job_id = '{}/{}'.format(fn['job_id'],'task')
            print('adding permission and notification to {} for JOBID {}'.format(job_bucket,job_id))
            l_fn.add_lambda_permission(random.randint(1,1000), job_bucket)
            l_fn.create_s3_eventsource_notification(s3_client,job_bucket,job_id)
        if 'bucket_listener' in fn:
            job_bucket = fn['bucket_listener']
            job_id = '{}/{}'.format(fn['job_id'],'result')
            l_fn.add_lambda_permission(random.randint(1,1000), job_bucket)
            l_fn.create_s3_eventsource_notification(s3_client,job_bucket,job_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='create-role')
    parser.add_argument('--profile','-p',action='store',default=None,help='AWS profile to use, omit argument if none')
    parser.add_argument('--update',action='store_true',default=False,help='Update the zip file and Lambda function, for Lambdas that we originally created (faster zipping)')
    parser.add_argument('--deleteAll',action='store_true',default=False,help='Delete the lambda functions that we originally created')
    parser.add_argument('--saveTriggerBucket',action='store_true',default=False,help='Used only if deleteAll is set, forces setupApps to keep job bucket.  setupApps removes the bucket contents if not set (left off).')
    parser.add_argument('--config','-f',action='store',default='setupconfig.json',help='Pass in the json configuration file instead of using setupconfig.json')
    parser.add_argument('--no_botocore_change',action='store_true',default=False,help='Do NOT prepare and upload botocore zip to S3. The one there from a prior run will work.')
    parser.add_argument('--turn_on_tracing',action='store_true',default=False,help='Turn on AWS Xray tracing.')
    parser.add_argument('--no_spotwrap',action='store_true',default=False,help='Do NOT inject SpotWrapSupport')
    parser.add_argument('--gammaRay',action='store_true',default=False,help='Inject gammaRay support')
    parser.add_argument('--with_fleece',action='store_true',default=False,help='Inject fleece support')
    parser.add_argument('--spotFnsTableName',action='store',default='gammaRays',help='Name of table which will hold SpotWrap writes. Arg is unused if --no_spotwrap is set.')
    parser.add_argument('--spotFnsTableRegion',action='store',default='us-west-2',help='AWS region in which table spotFns is located (for all SpotWrap writes). Arg is unused if --no_spotwrap is set.')
    args = parser.parse_args()
    if args.with_fleece and args.gammaRay:
        print('Error, fleece and gammaRay options cannot be used together.  Choose one.')
        sys.exit(1)
    if args.with_fleece and not args.no_spotwrap:
        print('Error, fleece and spotwrap options (add --no_spotwrap tor turn off) cannot be used together.  Choose one.')
        sys.exit(1)
    if args.update and args.deleteAll:
        print('Error, update and deleteAll options cannot be used together.  Choose one.')
        sys.exit(1)
    if args.gammaRay and not args.no_spotwrap:
        print('Error, must set --gammaRay and --no_spotwrap to use the gammaRay support')
        sys.exit(1)
    if args.gammaRay and args.turn_on_tracing:
        print('Error, --gammaRay and --turn_on_tracing cannot be used together')
        sys.exit(1)
    if args.turn_on_tracing:
        args.no_spotwrap = True #safety condition
    if not os.path.isfile(args.config):
        print('Error, no json config file found!')
        sys.exit(1)
    if args.gammaRay and args.no_spotwrap:
        args.turn_on_tracing = False
    if args.turn_on_tracing:
        args.no_boto_core_change = True
   
    processLambda(args.config,
        args.profile,
        args.no_spotwrap,
        args.update,
        args.deleteAll,
        args.no_botocore_change,
        args.spotFnsTableRegion,
        args.spotFnsTableName,
        args.saveTriggerBucket,
        args.turn_on_tracing,
        args.gammaRay,
        args.with_fleece
    )
