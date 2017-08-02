# MapReduce in Lambda
The original application from which this benchmark has been created can be found here: https://github.com/awslabs/lambda-refarch-mapreduce
We include the license from this original application.  All modifications fall under the repo license found here: https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/blob/master/LICENSE

Modifications include porting driver and setup code to Python3, support for AWS profiles (--profile PROFILENAME), support for SpotWrap for each of the 3 lambda functions, and modfications of the socket timeouts to avoid timeout errors.  

To run the benchmark, you must have the AWS CLI set up. Your credentials must have access to create and invoke Lambda and access to list, read, and write to a S3 bucket.

1. Create your S3 bucket to store the intermediate and final results.  Replace MY-BUCKET-NAME with your own unique name.  

   $ aws s3 mb s3://MY-BUCKET-NAME

2. Update the policy.json with your S3 bucket name (replace MY-S3-BUCKET with your bucket name from the previous step).  

3. Create the IAM role with respective policy  
```python
#This assumes you are using the SpotWrap virtual environment (venv)
cd setup
#Replace YOUR_PROFILE_NAME with the profile you wish to use, or leave off the option to use the root account; replace ROLENAME and POLICYNAME with names of your choosing
python create-role.py --profile YOUR_PROFILE_NAME ROLENAME POLICYNAME
```  

4. Use the output ARN from the script (or get it from the IAM Management Console under Roles). 
Set the serverless_mapreduce_role environment variable (replace MY_ACCOUNT_ID with your AWS account ID):   

   $ export serverless_mapreduce_role=arn:aws:iam::MY-ACCOUNT-ID:role/ROLENAME

5. The app consists of 4 lambda functions: driver, mapper, reducer, and reducerCoordinator.  The driver starts the process and invokes mappers in parallel either asynchronously (Event) or synchronously (RequestResponse) -- (see settings for this are below). Mappers get their data from the input data bucket ("bucket" argument) from the big data benchmark suite.  It processes data that have the prefix ("prefix" argument) specified and generates files in MY-BUCKET-NAME ("jobBucket" argument) under task/mapper/.  Generation of these files triggers (job_id/task prefix for a given job_id) the reducerCoordinator which spawns the reducers once the mappers are done ("Mappers Done so far" message in logs equals max mappers).  The reducerCoordinator reports "Job done!!! Check the result file" when everything has completed.

The reducers process the mapper data in parallel and asychronously, and write their results to the bucket under tasks/reducer/.  The overall app computes how many entries are made for each unique IP address prefix.

Use the "dryrun":"yes" key/value pair as an argument to only run the driver and see how many mappers (and then reducers) will be spawned.  

lambdaMemory for mapper and reducer functions must be 1536.  

The lambda timeout (300s) for the driver may be exceeded when run in synchronous mode.  In this case, the total timings will not be report but most likely all mappers will be spawned.  To see the timings, you can run the driver locally via ```python driver.py MY-BUCKET-NAME JOBID --wait4reducers``` replacing MY-BUCKET-NAME and JOBID (with the job prefix in the reducerCoordinator entry in the configuration below, up to /task, e.g. job1000).

Mapper and reducer "name" entries in the configuration below must not change (if you do change them, then update driver.py FunctionName and reducer_lambda_name variables).

Upload the functions to Lambda using the following. 
```
cd UCSBFaaS-Wrappers/lambda-python
python setupApps.py --profile cjk1 -f scns.json --no_spotwrap
cat scns.json    #replace MY-BUCKET-NAME for reduceCoordinator
{
        "region": "us-west-2",
        "functions": [
            {
                "name": "driverNS",
           	"lambdaMemory": 128,
                "handler": "driver.handler",
                "zip": "driverzip.zip",
                "files_and_dirs": [
                    "mr/driver.py",
                    "mr/lambdautils.py"
                ]
            },
            {
                "name": "mapper",
           	"lambdaMemory": 1536,
                "handler": "mapper.handler",
                "zip": "mapperzip.zip",
                "files_and_dirs": [
                    "mr/mapper.py"
                ]
            },
            {
                "name": "reducer",
           	"lambdaMemory": 1536,
                "handler": "reducer.handler",
                "zip": "reducerzip.zip",
                "files_and_dirs": [
                    "mr/reducer.py"
                ]
            },
            {
                "name": "reducerCoordinatorNS",
           	"lambdaMemory": 128,
                "handler": "reducerCoordinator.handler",
                "zip": "reducerCoordinatorzip.zip",
                "files_and_dirs": [
                    "mr/reducerCoordinator.py",
                    "mr/lambdautils.py"
                ],
                "permission": "MY-BUCKET-NAME",
                "job_id": "job1000/task"
            }
        ]
}
```
6. **Run It**. Replace MY-BUCKET-NAME below.  
Make sure that job_id value below matches the prefix (prior to /task) in the reducerCoordinator configuration entry above (job1000).  The job takes approximately 5 minutes to complete and can be run synchronously (mappers are in parallel) or fully asynchronous (omit the "full_async" argument).  
"Job done!!! Check the result file" in one of the reducerCoordinator logs signals app completion.  

The region argument must match that in the setupApps configuration above. Replace awsprofile1 below with your AWS IAM profile. Keep the settings for prefix and bucket as that is where the original datasets from the big data benchmark are located.
```
#dry run (do not run mappers or reducers, just see how many of each there will be
aws lambda invoke --invocation-type Event --function-name driverNS --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","prefix":"pavlo/text/1node/uservisits/","bucket":"big-data-benchmark","dryrun":"yes"}' outputfile
#synchronously
aws lambda invoke --invocation-type Event --function-name driverNS --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","prefix":"pavlo/text/1node/uservisits/","bucket":"big-data-benchmark","job_id":"job1000","jobBucket":"MY-BUCKET-NAME","region":"us-west-2"}' outputfile
//See the driverNS CloudWatch log for progress

#asynchronously
aws lambda invoke --invocation-type Event --function-name driverNS --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","prefix":"pavlo/text/1node/uservisits/","bucket":"big-data-benchmark","job_id":"job1000","jobBucket":"MY-BUCKET-NAME","region":"us-west-2","full_async":"yes"}' outputfile
//Wait for two reducerNS CloudWatch logs to complete, one with contents "
```

7. Clean up (delete everything: lambdas, logs, bucket contents)
```
cd UCSBFaaS-Wrappers/lambda-python
python setupApps.py --profile cjk1 -f scns.json --deleteAll

#or delete everything except bucket contents
python setupApps.py --profile cjk1 -f scns.json --deleteAll --saveTriggerBucket
```

----------------------------
#Add SpotWrap Support to MR
1. Delete all previous lambda functions of the same name
```
cd UCSBFaaS-Wrappers/lambda-python
python setupApps.py --profile cjk1 -f scns.json --deleteAll
```
