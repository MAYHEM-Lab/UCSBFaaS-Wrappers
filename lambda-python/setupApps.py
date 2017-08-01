'''
 Driver to deploy SpotWrapped Apps
 Author: Chandra Krintz
 License and Copyright in ../LICENSE
'''
import boto3,botocore,json
import sys,time,glob,subprocess,argparse,os,tempfile,shutil
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
        (with contents) when unzipped
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

def processLambda(config_fname, profile, noWrap=False, update=False, deleteThem=False, noBotocore=False):
    if profile:
        boto3.setup_default_session(profile_name=profile)
    config = botocore.client.Config(connect_timeout=50, read_timeout=100)
    lambda_client = boto3.client('lambda',config=config)
    s3 = None
    if not noBotocore:
        s3 = boto3.resource('s3')
    spotwraptemplate = 'SpotWrap.py.template'
    spotwrapfile = 'SpotWrap.py'

    # Config
    config = json.loads(open(config_fname, 'r').read())
    region = config['region']
    lambda_memory = config['lambdaMemory']
    fns = config['functions']
    #Create the lambda functions
    for fn in fns:
        name = fn['name']
        if deleteThem: #don't do anything more if we are deleting
            try:
                l_fn = lambdautils.LambdaManager(lambda_client, region, None, name, None)
                l_fn.delete_function()
            except:
                pass
            try:
                lambdautils.LambdaManager.cleanup_logs(name)
            except:
                pass
            print('setupApps: {} deleted'.format(name))
            continue #get the next function to delete

        #else process the rest and create the Lambda
        ziplist = fn['files_and_dirs']
        zipfile = fn['zip']
        handler = fn['handler'] #must be of the form filename.handlername
        periods = handler.count('.')
        peridx = handler.find('.')
        if periods != 1 or peridx == 0:
            print('Error, the handler entry for {} must be of the form filename.handlername.  Please fix and rerun.'.format(name))
            sys.exit(1)

        ''' Process the patched botocore file (place in S3 for SpotWrap.py to download)''' 
        botozipdir = None
        zipbase = 'botocore_patched.zip'
        zipname = '/tmp/'.format(zipbase) #this much match same in SpotWrap.py.template

        if 'patched_botocore_dir' not in fn or fn['patched_botocore_dir'] == '': #no patch dir specified
            print('patched_botocore_dir not set in configuration file. To inject SpotWrap support, set this value and rerun this program. Not injecting SpotWrap support...')
            noWrap = True
        else:
            if 'patched_botocore_dir' in fn:
                botozipdir = fn['patched_botocore_dir']
                if not os.path.isdir(botozipdir):
                    noWrap = True

        s3bkt = 'spotbucket'
        if not noWrap and ('s3bucket' not in fn or fn['s3bucket'] == ''): #double check that this exists
            print('No s3 bucket name (s3bucket) found in configuration file. Not injecting SpotWrap support...')
            noWrap = True
        elif not noWrap: #s3bucket is set, check that it is a valid S3 bucket
            s3bkt = fn['s3bucket']
            if not noBotocore:
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
        tmp_dir = None
        if not noWrap: 
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
                # Write the file out 
                with open(target, 'w') as f:
                    f.write(filedata)

                print('setupApps: SpotWrap support inserted')

        l_zip = zipLambda(zipfile,ziplist,update)
        if tmp_dir:
            shutil.rmtree(tmp_dir)

        l_fn = lambdautils.LambdaManager(lambda_client, region, l_zip, name, handler)
        l_fn.update_code_or_create_on_noexist()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='create-role')
    parser.add_argument('--profile','-p',action='store',default=None,help='AWS profile to use, omit argument if none')
    parser.add_argument('--update',action='store_true',default=False,help='Update the zip file and Lambda function, for Lambdas that we originally created (faster zipping)')
    parser.add_argument('--deleteAll',action='store_true',default=False,help='Delete the lambda functions that we originally created')
    parser.add_argument('--config','-f',action='store',default='setupconfig.json',help='Pass in the json configuration file instead of using setupconfig.json')
    parser.add_argument('--no_botocore_change',action='store_true',default=False,help='Do NOT prepare and upload botocore zip to S3. The one there from a prior run will work.')
    parser.add_argument('--no_spotwrap',action='store_true',default=False,help='Do NOT inject SpotWrapSupport')
    args = parser.parse_args()
    if args.update and args.deleteAll:
        print('Error, update and deleteAll options cannot be used together.  Choose one.')
        sys.exit(1)
    processLambda(args.config,args.profile,args.no_spotwrap,args.update,args.deleteAll,args.no_botocore_change)
