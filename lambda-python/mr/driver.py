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

def invoke_lambda(batches,mapper_outputs,bucket,job_bucket,job_id,m_id):
    '''
    lambda invoke function
    '''
    config = botocore.client.Config(connect_timeout=50, read_timeout=200)
    lambda_client = boto3.client('lambda',config=config)

    batch = [k.key for k in batches[m_id-1]]
    resp = lambda_client.invoke( 
            FunctionName = 'mapperNOSPOT',
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
    job_id = event["job_id"]
    bucket = event["bucket"]
    job_bucket = event["jobBucket"]
    region = event["region"]
    lambda_memory = 1536
    concurrent_lambdas = event["concurrentLambdas"]
    reducer_lambda_name = "reducerNOSPOT"
    
    # Fetch all the keys that match the prefix
    all_keys = []
    print(bucket)
    for obj in s3.Bucket(bucket).objects.filter(Prefix=event["prefix"]).all():
        all_keys.append(obj)
    
    bsize = lambdautils.compute_batch_size(all_keys, lambda_memory)
    batches = lambdautils.batch_creator(all_keys, bsize)
    n_mappers = len(batches)
    
    # Write Jobdata to S3
    j_key = job_id + "/jobdata";
    data = json.dumps({
                    "mapCount": n_mappers, 
                    "totalS3Files": len(all_keys),
                    "startTime": time.time()
                    })
    write_to_s3(s3, job_bucket, j_key, data, {})
    #write_job_config(job_id, job_bucket, n_mappers, reducer_lambda_name, "{}.handler".format(reducer_lambda_name)) #local write won't work, put instead in s3
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
    
    mapper_outputs = []
    print("# of Mappers ", n_mappers)
    pool = ThreadPool(n_mappers)
    Ids = [i+1 for i in range(n_mappers)]
    invoke_lambda_partial = partial(invoke_lambda, batches,mapper_outputs,bucket,job_bucket,job_id)
    
    # Burst request handling
    mappers_executed = 0
    while mappers_executed < n_mappers:
        nm = min(concurrent_lambdas, n_mappers)
        results = pool.map(invoke_lambda_partial, Ids[mappers_executed: mappers_executed + nm])
        mappers_executed += nm
    
    pool.close()
    pool.join()
    
    print("all the mappers finished")
    
    total_s3_get_ops = 0
    s3_storage_hours = 0
    total_lines = 0
    total_lambda_secs = 0
    
    for output in mapper_outputs:
        total_s3_get_ops += int(output[0])
        total_lines += int(output[1])
        total_lambda_secs += float(output[2])
    
    #Note: Wait for the job to complete so that we can compute total cost ; create a poll every 10 secs
    # Get all reducer keys
    reducer_keys = []
    
    # Total execution time for reducers
    reducer_lambda_time = 0
    
    while True:
        job_keys = s3_client.list_objects(Bucket=job_bucket, Prefix=job_id)["Contents"]
        keys = [jk["Key"] for jk in job_keys]
        total_s3_size = sum([jk["Size"] for jk in job_keys])
        
        print( "check to see if the job is done")
    
        # check job done
        if job_id + "/result" in keys:
            print("job done")
            reducer_lambda_time += float(s3.Object(job_bucket, job_id + "/result").metadata['processingtime'])
            for key in keys:
                if "task/reducer" in key:
                    reducer_lambda_time += float(s3.Object(job_bucket, key).metadata['processingtime'])
                    reducer_keys.append(key)
            break
        time.sleep(5)
    
    total_s3_get_ops += len(job_keys) 
    print('total_s3_get_ops:{}:total_lines:{}:total_map_secs:{}:mappers:{}:total_red_secs:{}'.format(total_s3_get_ops,total_lines,total_lambda_secs,n_mappers,reducer_lambda_time))
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MRDriver')
    parser.add_argument('jobbkt',action='store',help='job bucket')
    parser.add_argument('jobid',action='store',help='unique jobid')
    parser.add_argument('--databkt',action='store',default='big-data-benchmark',help='data bucket')
    parser.add_argument('--region',action='store',default='us-west-2',help='job bucket')
    args = parser.parse_args()
    event = {}
    event['prefix'] = "pavlo/text/1node/uservisits/"
    event['eventSource'] = "ext:invokeCLI"
    event['job_id'] = args.jobid
    event['bucket'] = args.databkt
    event['jobBucket'] = args.jobbkt
    event['region'] = args.region
    event['concurrentLambdas'] = 50
    handler(event,None)
