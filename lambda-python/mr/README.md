#one with contents  MapReduce in Lambda
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

   $ export AWSRole=arn:aws:iam::MY-ACCOUNT-ID:role/ROLENAME

5. The app consists of 4 lambda functions: driver, mapper, reducer, and reducerCoordinator.  The driver starts the process and invokes mappers in parallel either asynchronously (Event) or synchronously (RequestResponse) -- (see settings for this are below). Mappers get their data from the input data bucket ("bucket" argument) from the big data benchmark suite.  It processes data that have the prefix ("prefix" argument) specified and generates files in MY-BUCKET-NAME ("jobBucket" argument) under JOBID/task/mapper/.  Generation of these files triggers the reducerCoordinator which spawns the reducers once the mappers are done ("Mappers Done so far" message in logs equals max mappers).  The reducerCoordinator reports "Job done!!! Check the result file" when everything has completed.

The reducers process the mapper data in parallel and asychronously, and write their results to the bucket under JOBID/tasks/reducer/.  The overall app computes how many entries are made for each unique IP address prefix.

Use the "dryrun":"yes" key/value pair as an argument to only run the driver and see how many mappers (and then reducers) will be spawned.  

lambdaMemory for mapper and reducer functions must be 1536.  

The lambda timeout (300s) for the driver may be exceeded when run in synchronous mode.  In this case, the total timings will not be report but most likely all mappers will be spawned.  To see the timings, you can run the driver locally via ```python driver.py MY-BUCKET-NAME JOBID mapperNS reducerNS --wait4reducers``` replacing MY-BUCKET-NAME and JOBID.  Remove the NS from the mapper and reducer lambda function names to run the app with spotwrap support (assuming the functions have been uploaded with SpotWrap support via setupApps.py -- more on this below).

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
                "name": "mapperNS",
           	"lambdaMemory": 1536,
                "handler": "mapper.handler",
                "zip": "mapperzip.zip",
                "files_and_dirs": [
                    "mr/mapper.py"
                ]
            },
            {
                "name": "reducerNS",
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
                "job_id": "job1000"
            }
        ]
}
```
6. **Run It**. Replace MY-BUCKET-NAME and job_id.
Make sure that job_id value below matches the prefix in the reducerCoordinator configuration entry above (job1000).  The job takes approximately 10 minutes to complete and can be run synchronously (mappers are in parallel) or fully asynchronous (if you add the "full_async" argument or omit the --wait4reducers CLI flag).  
"Job done!!! Check the result file" in one of the reducerCoordinator logs signals app completion.  

The region argument must match that in the setupApps configuration above. Replace awsprofile1 below with your AWS IAM profile. Keep the settings for prefix and bucket as that is where the original datasets from the big data benchmark are located.
```
#Replace MY-BUCKET-NAME and JOBID, JOBID must match the JOBID prefix in the config file for the reducerCoordinator entry.
#dry run only (count mappers)
python driver.py MY-BUCKET-NAME JOBID --dryrun
#run short and synchronously
python driver.py MY-BUCKET-NAME JOBID MAPPER_FN_NAME REDUCER_FN_NAME --wait4reducers --endearly 2
#run short and asynchronously
python driver.py MY-BUCKET-NAME JOBID MAPPER_FN_NAME REDUCER_FN_NAME --endearly 2
#run full and asynchrously
python driver.py MY-BUCKET-NAME JOBID MAPPER_FN_NAME REDUCER_FN_NAME

#or use invoke to execute the driver in AWS Lambda and pass in the flags as JSON args:
#driver name must match "name" of driver.py entry in config file.
#region must match the region of the functions in the config file.
#mapper and reducer must be lambda functions in AWS; use full_async set to anything to run asynchronously
#leave off the endearly option to run the full version (here it says run just 2 mappers/reducers).
#eventSource will be ignored if SpotWrap not in use
#remove NS if you wish to run the lambdas with spotwrap support, but don't mix and match
aws lambda invoke --invocation-type Event --function-name driverNS --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","prefix":"pavlo/text/1node/uservisits/","job_id":"JOBID","bucket":"big-data-benchmark","jobBucket":"MY-BUCKET-NAME","full_async":"yes","endearly":2,"mapper":"mapperNS","reducer":"reducerNS"}' outputfile

#dry run (do not run mappers or reducers, just see how many of each there will be
#remove NS if you wish to run the lambdas with spotwrap support, but don't mix and match
aws lambda invoke --invocation-type Event --function-name driverNS --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","prefix":"pavlo/text/1node/uservisits/","bucket":"big-data-benchmark","dryrun":"yes","mapper":"mapperNS","reducer":"reducerNS"}' outputfile

#synchronously
#remove NS if you wish to run the lambdas with spotwrap support, but don't mix and match
aws lambda invoke --invocation-type Event --function-name driverNS --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","prefix":"pavlo/text/1node/uservisits/","bucket":"big-data-benchmark","job_id":"JOBID","jobBucket":"MY-BUCKET-NAME","region":"us-west-2","mapper":"mapperNS","reducer":"reducerNS"}' outputfile
//See the driverNS CloudWatch log for progress, WARNING driverNS may be killed if it takes over 300s, which it sometimes might (use async instead)

#asynchronously
#remove NS if you wish to run the lambdas with spotwrap support, but don't mix and match
aws lambda invoke --invocation-type Event --function-name driverNS --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","prefix":"pavlo/text/1node/uservisits/","bucket":"big-data-benchmark","job_id":"JOBID","jobBucket":"MY-BUCKET-NAME","region":"us-west-2","full_async":"yes","mapper":"mapperNS","reducer":"reducerNS"}' outputfile
//Wait for two reducerNS CloudWatch logs to complete (for "Job done!")
```

7. Clean up (delete everything: lambdas, logs, bucket contents)
```
cd UCSBFaaS-Wrappers/lambda-python
python setupApps.py --profile cjk1 -f scns.json --deleteAll

#or delete everything except bucket contents
python setupApps.py --profile cjk1 -f scns.json --deleteAll --saveTriggerBucket
```

The full usage for the driver program is here (it can be run as an AWS Lambda or via the command line):
```
usage: driver.py [-h] [--databkt DATABKT] [--prefix PREFIX] [--region REGION]
                 [--wait4reducers] [--dryrun] [--endearly ENDEARLY]
                 jobbkt jobid

MRDriver

positional arguments:
  jobbkt               job bucket for output files (that trigger reducers)
  jobid                unique jobid - must match the S3 job_id in trigger
                       (bucket prefix: permission/job_id) specified in
                       ../setupconfig.json for reducerCoordinator installation
                       by setupApps
  mapper_function      AWS Function Name of mapper function
  reducer_function     AWS Function Name of reducer function


optional arguments:
  -h, --help           show this help message and exit
  --databkt DATABKT    input data bucket
  --prefix PREFIX      prefix of data files in input data bucket
  --region REGION      job bucket
  --wait4reducers      Wait 4 reducers to finish and report their timings
  --dryrun             see how many mappers are needed then exit (do not run
                       the mapreduce job)
  --endearly ENDEARLY  For debugging, start endearly mappers then stop
```

----------------------------

# Add SpotWrap Support to MR

1. Delete all previous lambda functions of the same name
```
cd UCSBFaaS-Wrappers/lambda-python
python setupApps.py --profile cjk1 -f scns.json --deleteAll
```
2. Change the configuration file to support SpotWrap.  Add these two lines:  
   "patched_botocore_dir": "venv/lib/python3.6/site-packages/botocore",
   "s3bucket": "cjktestbkt"
   To the end of each function entry after the files_and_dirs array.  Don't forget to add your comma at the end of the array. Change CODE_BUCKET to a bucket name of your choosing, make one if you need to.  E.g.
```
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
            ],
            "patched_botocore_dir": "venv/lib/python3.6/site-packages/botocore",
            "s3bucket": "CODE_BUCKET"
        }
    ]
}
```

4. Generate the functions with SpotWrap support.  Once you do this the first time, you can then use the --no_botocore_change flag for subsequent invocations to make it go faster.  Without this flag, setupApps builds the zip file for the botocore changes and puts them in S3 so that SpotWrap can grab them upon first function invocation.  If you don't change this code, you only need to run this once to put it in S3.
```
cd UCSBFaaS-Wrappers/lambda-python
python setupApps.py --profile cjk1 -f scns.json
```

5. **Run It**  See step 6 in first part (same as without SpotWrap)

#Troubleshooting
   * If you get this error:  
   ```botocore.errorfactory.NoSuchBucket: An error occurred (NoSuchBucket) when calling the PutBucketNotificationConfiguration operation: The specified bucket does not exist
   ```
   Update your the file with the your CODEBUCKET (and bucket with read/write access), MY-BUCKET-NAME, and JOBID.
   * If your app goes rogue in AWS Lambda and you want to kill it midstream, use ```python setupApps.py --profile cjk1 -f scns.json --deleteAll``` repeatedly and everything will eventually stop and be deleted (running functions must complete).  Its a good idea to change the JOBID when this happens so that you are sure that nothing old is being triggered.  Do this after running deleteAll, then change the configuration (reducerCoordinator object), and then rerun setupApps to reload new lambdas.  Then use the updated JOBID on the commandline (locallay or in AWS Lambda).
   * If you want to run a short version of this app, use the ```endearly``` flag set to some integer lower than 29.  The app will only execute this many mappers (and reducers).  E.g., ```python driver.py MY-BUCKET-NAME JOBID mapperNS reducerNS --endearly 2``` for two mappers/reducers.  To do the same through the driver in AWS Lambda, use ```aws lambda invoke --invocation-type Event --function-name driverNS --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","prefix":"pavlo/text/1node/uservisits/","job_id":"JOBID","bucket":"big-data-benchmark","jobBucket":"MY-BUCKET-NAME","full_async":"yes","endearly":2,"mapper":"mapperNS","reducer":"reducerNS"}' outputfile```
