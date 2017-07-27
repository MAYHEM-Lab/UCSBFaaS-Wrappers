# MapReduce Benchmark for AWS Lambda

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

5. Make edits to driverconfig.json to update "jobBucket": "MY-BUCKET-NAME", replacing MY-BUCKET-NAME with the bucketname you created in step 1.


6. Run the driver, defaults used are 50 concurrent lambdas and the us-west-2 region.  Update these values in driverconfig.json as appropriate.
 
	$ python driver.py

Additional details on running the original app can be found here: https://github.com/awslabs/lambda-refarch-mapreduce

Example output from driver.py for a successful run:
```
python driver.py
big-data-benchmark
Dataset size: 26186978239.0, nKeys: 202, avg: 129638506.13366337
updating: mapper.py (deflated 54%)
updating: jobinfo.json (deflated 37%)
updating: lambdautils.py (deflated 65%)
updating: reducer.py (deflated 55%)
updating: jobinfo.json (deflated 37%)
updating: lambdautils.py (deflated 65%)
updating: reducerCoordinator.py (deflated 64%)
updating: jobinfo.json (deflated 37%)
updating: lambdautils.py (deflated 65%)
{'ResponseMetadata': {'RequestId': 'e0b6f59a-731a-11e7-b1b2-47f9a33473e4', 'HTTPStatusCode': 200, 'HTTPHeaders': {'content-type': 'application/json', 'date': 'Thu, 27 Jul 2017 22:28:12 GMT', 'x-amzn-requestid': 'e0b6f59a-731a-11e7-b1b2-47f9a33473e4', 'content-length': '583', 'connection': 'keep-alive'}, 'RetryAttempts': 0}, 'FunctionName': 'yyy-mapper-yyy-release', 'FunctionArn': 'arn:aws:lambda:us-west-2:XXX:function:yyy-mapper-yyy-release:1', 'Runtime': 'python2.7', 'Role': 'arn:aws:iam::XXX:role/spotMRlambda_role', 'Handler': 'mapper.lambda_handler', 'CodeSize': 3660, 'Description': 'yyy-mapper-yyy-release', 'Timeout': 300, 'MemorySize': 1536, 'LastModified': '2017-07-27T22:28:13.670+0000', 'CodeSha256': '6faJqM5oi0Y/OBunwrnWQMzQzDaw3y0rKKdnOLx5I64=', 'Version': '1', 'TracingConfig': {'Mode': 'PassThrough'}}
{'ResponseMetadata': {'RequestId': 'e0f8e058-731a-11e7-8803-ad4ea378804f', 'HTTPStatusCode': 200, 'HTTPHeaders': {'content-type': 'application/json', 'date': 'Thu, 27 Jul 2017 22:28:13 GMT', 'x-amzn-requestid': 'e0f8e058-731a-11e7-8803-ad4ea378804f', 'content-length': '587', 'connection': 'keep-alive'}, 'RetryAttempts': 0}, 'FunctionName': 'yyy-reducer-yyy-release', 'FunctionArn': 'arn:aws:lambda:us-west-2:XXX:function:yyy-reducer-yyy-release:1', 'Runtime': 'python2.7', 'Role': 'arn:aws:iam::XXX:role/spotMRlambda_role', 'Handler': 'reducer.lambda_handler', 'CodeSize': 3742, 'Description': 'yyy-reducer-yyy-release', 'Timeout': 300, 'MemorySize': 1536, 'LastModified': '2017-07-27T22:28:13.960+0000', 'CodeSha256': 'Mbul3xrAoYJeEssFzXE5ptztw55em9jL6AG8mXxUq7E=', 'Version': '1', 'TracingConfig': {'Mode': 'PassThrough'}}
{'ResponseMetadata': {'RequestId': 'e1653708-731a-11e7-81be-5517c076039d', 'HTTPStatusCode': 200, 'HTTPHeaders': {'content-type': 'application/json', 'date': 'Thu, 27 Jul 2017 22:28:14 GMT', 'x-amzn-requestid': 'e1653708-731a-11e7-81be-5517c076039d', 'content-length': '583', 'connection': 'keep-alive'}, 'RetryAttempts': 0}, 'FunctionName': 'yyy-rc-yyy-release', 'FunctionArn': 'arn:aws:lambda:us-west-2:XXX:function:yyy-rc-yyy-release:1', 'Runtime': 'python2.7', 'Role': 'arn:aws:iam::XXX:role/spotMRlambda_role', 'Handler': 'reducerCoordinator.lambda_handler', 'CodeSize': 4875, 'Description': 'yyy-rc-yyy-release', 'Timeout': 300, 'MemorySize': 1536, 'LastModified': '2017-07-27T22:28:14.672+0000', 'CodeSha256': 't5Nz5LPHVmDXgMAdXUzsRJqXGowTMe5+NFPWGWeqgTY=', 'Version': '1', 'TracingConfig': {'Mode': 'PassThrough'}}
{'ResponseMetadata': {'RequestId': 'e1845766-731a-11e7-b1b2-47f9a33473e4', 'HTTPStatusCode': 201, 'HTTPHeaders': {'content-type': 'application/json', 'date': 'Thu, 27 Jul 2017 22:28:13 GMT', 'x-amzn-requestid': 'e1845766-731a-11e7-b1b2-47f9a33473e4', 'content-length': '302', 'connection': 'keep-alive'}, 'RetryAttempts': 0}, 'Statement': '{"Sid":"720","Resource":"arn:aws:lambda:us-west-2:XXX:function:yyy-rc-yyy-release","Effect":"Allow","Principal":{"Service":"s3.amazonaws.com"},"Action":["lambda:InvokeFunction"],"Condition":{"ArnLike":{"AWS:SourceArn":"arn:aws:s3:::spot-mr-bkt"}}}'}
# of Mappers  29
mapper output [6, 4678290, 80.57181596755981, '']
mapper output [7, 5441371, 89.42336511611938, '']
mapper output [7, 5441035, 89.38957381248474, '']
mapper output [7, 5439425, 89.4409511089325, '']
mapper output [7, 5442051, 93.78048205375671, '']
mapper output [7, 5443517, 94.03341102600098, '']
mapper output [7, 4686731, 94.83944892883301, '']
mapper output [7, 5443126, 95.80179023742676, '']
mapper output [7, 5438671, 96.57802104949951, '']
mapper output [7, 5373857, 96.56180214881897, '']
mapper output [7, 5441766, 81.07890582084656, '']
mapper output [7, 5440302, 82.95203804969788, '']
mapper output [7, 5440926, 82.58147382736206, '']
mapper output [7, 5439635, 85.52894592285156, '']
mapper output [7, 5442404, 85.37363696098328, '']
mapper output [7, 5373873, 89.35961103439331, '']
mapper output [7, 5444960, 89.24763321876526, '']
mapper output [7, 5376303, 91.55505895614624, '']
mapper output [7, 5443046, 90.92856097221375, '']
mapper output [7, 5445883, 94.25224614143372, '']
mapper output [7, 5434537, 92.11726713180542, '']
mapper output [7, 5445750, 82.25830507278442, '']
mapper output [7, 5373925, 90.61918902397156, '']
mapper output [7, 5374102, 91.68397903442383, '']
mapper output [7, 5444580, 93.48136901855469, '']
mapper output [7, 4616974, 94.7377610206604, '']
mapper output [7, 5375092, 76.59697198867798, '']
mapper output [7, 5442738, 89.3367829322815, '']
mapper output [7, 5375127, 92.60600304603577, '']
all the mappers finished
check to see if the job is done
job done
Reducer L 0.0019023833491122045
Lambda Cost 0.06683327694669837
S3 Storage Cost 3.238303306591948e-05
S3 Request Cost 0.00025360000000000004
S3 Cost 0.00028598303306591954
Total Cost:  0.06711925997976428
Total Lines: 154999997
```
