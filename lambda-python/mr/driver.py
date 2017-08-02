'''
 Driver to start mapreduce using AWS Lambda
'''

import boto3,botocore,json,math,random,re,sys,time,argparse,logging
import lambdautils
from multiprocessing.dummy import Pool as ThreadPool
from functools import partial

### GLOBALS ####

### UTILS ####
def write_to_s3(s3, bucket, key, data, metadata):
    s3.Bucket(bucket).put_object(Key=key, Body=data, Metadata=metadata)

def write_job_config(job_id, job_bucket, n_mappers, r_func, r_handler):
    fname = "jobinfo.json"; 
    with open(fname, 'w') as f:
        data = json.dumps({
            "jobId": job_id,
            "jobBucket" : job_bucket,
            "mapCount": n_mappers,
            "reducerFunction": r_func,
            "reducerHandler": r_handler
            }, indent=4);
        f.write(data)

def invoke_lambda(batches,bucket,job_bucket,job_id,m_id):
    '''
    lambda invoke function asynchronously
    '''
    config = botocore.client.Config(connect_timeout=50, read_timeout=200)
    lambda_client = boto3.client('lambda',config=config)

    batch = [k.key for k in batches[m_id-1]]
    resp = lambda_client.invoke( 
            FunctionName = 'mapper',
            InvocationType = 'Event',
            Payload =  json.dumps({
                "bucket": bucket,
                "keys": batch,
                "jobBucket": job_bucket,
                "jobId": job_id,
                "mapperId": m_id
            })
        )

def invoke_lambda_sync(batches,mapper_outputs,bucket,job_bucket,job_id,m_id):
    '''
    lambda invoke function synchronously using partial and threads
    '''
    config = botocore.client.Config(connect_timeout=50, read_timeout=200)
    lambda_client = boto3.client('lambda',config=config)

    batch = [k.key for k in batches[m_id-1]]
    resp = lambda_client.invoke( 
            FunctionName = 'mapper',
            InvocationType = 'RequestResponse',
            Payload =  json.dumps({
                "bucket": bucket,
                "keys": batch,
                "jobBucket": job_bucket,
                "jobId": job_id,
                "mapperId": m_id
            })
        )
    out = eval(resp['Payload'].read())
    mapper_outputs.append(out)
    print("mapper output", out)

def handler(event, context):
    entry = time.time() * 1000
    logger = logging.getLogger()
    logger.setLevel(logging.WARN)
    if not event: #requires arguments
        return

    # create an S3 session
    if not context: #calling from main
        boto3.setup_default_session(profile_name='cjk1')
    s3 = boto3.resource('s3')
    config = botocore.client.Config(connect_timeout=50, read_timeout=200)
    s3_client = boto3.client('s3',config=config)

    JOB_INFO = 'jobinfo.json'

    # 1. Get all keys to be processed  
    # init 
    endearly = 0
    if 'endearly' in event:
        endearly = int(event['endearly'])
    bucket = event["bucket"]
    dryrun = True if "dryrun" in event else False
    lambda_memory = 1536

    # Fetch all the keys that match the prefix
    all_keys = []
    for obj in s3.Bucket(bucket).objects.filter(Prefix=event["prefix"]).all():
        all_keys.append(obj)
    
    bsize = lambdautils.compute_batch_size(all_keys, lambda_memory)
    batches = lambdautils.batch_creator(all_keys, bsize)
    n_mappers = len(batches)
    if endearly > 0 and endearly < n_mappers:
        n_mappers = endearly
    print("Num. of Mappers (and Reducers) ", n_mappers)

    if dryrun: #don't go any further
        delta = (time.time() * 1000) - entry
        me_str = 'TIMER:CALL:{}:dryrun:0'.format(delta)
        logger.warn(me_str)
        return me_str

    #process the remaining arguments
    job_id = event["job_id"]
    job_bucket = event["jobBucket"]
    region = event["region"]
    async = True if "full_async" in event else False
    reducer_lambda_name = "reducer"
    
    # Write Jobdata to S3
    j_key = job_id + "/jobdata";
    data = json.dumps({
        "mapCount": n_mappers, 
        "totalS3Files": len(all_keys),
        "startTime": time.time()
        })
    write_to_s3(s3, job_bucket, j_key, data, {})
    data = json.dumps({
        "jobId": job_id,
        "jobBucket" : job_bucket,
        "mapCount": n_mappers,
        "reducerFunction": reducer_lambda_name,
        "reducerHandler": "{}.handler".format(reducer_lambda_name)
        }, indent=4);
    j_key = job_id + "/jobinfo.json";
    write_to_s3(s3,job_bucket,j_key,data,{})

    ### Execute ###
    total_lambda_secs = 0
    reducer_lambda_time = 0
    mapper_outputs = []

    if async: #asynchronous invocation of mappers
        for i in range(n_mappers):
            invoke_lambda(batches,bucket,job_bucket,job_id,i)

    else: #synchronous invocation of mappers on parallel threads
        pool = ThreadPool(n_mappers)
        Ids = [i+1 for i in range(n_mappers)]
        invoke_lambda_partial = partial(invoke_lambda_sync,batches,mapper_outputs,bucket,job_bucket,job_id)
        
        # Burst request handling
        mappers_executed = 0
        concurrent_lambdas = 100 #only used by synchronous run (use --dryrun to see how many actual mappers are needed
        while mappers_executed < n_mappers:
            nm = min(concurrent_lambdas, n_mappers)
            results = pool.map(invoke_lambda_partial, Ids[mappers_executed: mappers_executed + nm])
            mappers_executed += nm
    
        pool.close()
        pool.join()
    
    for output in mapper_outputs:
        if 'body' in output:
            total_lambda_secs += float(output['body'][2])
        else:
            total_lambda_secs += float(output[2])
    
    if not async:
        #Note: Wait for the job to complete so that we can compute total cost ; create a poll every 10 secs
        # Get all reducer keys
        reducer_keys = []
        # Total execution time for reducers
    
        while True:
            job_keys = s3_client.list_objects(Bucket=job_bucket, Prefix=job_id)["Contents"]
            keys = [jk["Key"] for jk in job_keys]
            total_s3_size = sum([jk["Size"] for jk in job_keys])
            
            logger.info("checking if job is done")
        
            # check job done
            if job_id + "/result" in keys:
                reducer_lambda_time += float(s3.Object(job_bucket, job_id + "/result").metadata['processingtime'])
                for key in keys:
                    if "task/reducer" in key:
                        reducer_lambda_time += float(s3.Object(job_bucket, key).metadata['processingtime'])
                        reducer_keys.append(key)
                break
            time.sleep(5)
        
    delta = (time.time() * 1000) - entry
    me_str = 'TIMER:CALL:{}:mappers:{}:reducer:{}'.format(delta,total_lambda_secs,reducer_lambda_time)
    logger.warn(me_str)
    return me_str
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MRDriver')
    parser.add_argument('jobbkt',action='store',help='job bucket for output files (that trigger reducers)')
    parser.add_argument('jobid',action='store',help='unique jobid - must match the S3 job_id in trigger (bucket prefix: permission/job_id) specified in ../setupconfig.json for reducerCoordinator installation by setupApps')
    parser.add_argument('--databkt',action='store',default='big-data-benchmark',help='input data bucket')
    parser.add_argument('--prefix',action='store',default='pavlo/text/1node/uservisits/',help='prefix of data files in input data bucket')
    parser.add_argument('--region',action='store',default='us-west-2',help='job bucket')
    parser.add_argument('--wait4reducers',action='store_false',default=True,help='Wait 4 reducers to finish and report their timings')
    parser.add_argument('--dryrun',action='store_true',default=False,help='see how many mappers are needed then exit (do not run the mapreduce job)')
    parser.add_argument('--endearly',action='store',default=0,help='For debugging, start endearly mappers then stop')
    args = parser.parse_args()
    event = {}
    event['prefix'] = args.prefix
    event['eventSource'] = "ext:invokeCLI"
    event['job_id'] = args.jobid
    event['bucket'] = args.databkt
    event['jobBucket'] = args.jobbkt
    event['region'] = args.region
    event['endearly'] = args.endearly
    if args.wait4reducers:
        event['full_async'] = "set_anything_here"
    if args.dryrun:
        event['dryrun'] = "set_anything_here"
    handler(event,None)
