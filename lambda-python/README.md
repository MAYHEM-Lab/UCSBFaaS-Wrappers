# SpotWrap 
SpotWrapper is a simple wrapper for Python3 AWS Lambda functions that enables tracing
of and connecting dependent events in AWS Lambda.  In this repo are three projects: SpotTemplate, dbMod, and s3Mod which produce three Lambda functions called SpotTemplatePy, dbModPy, s3ModPy, and FnInvokerPy.
SpotTemplatePy handles different Lambda triggers and logs them, and then invokes another Lambda funcction if a Lambda ARN has been passed into it.  dbModPy reads and writes to AWS DynamoDB; s3ModPy writes to AWS S3; SNSPy posts a notification to AWS SNS; FnInvokerPy invokes 1+ function instances.

This repo also contains a tool called setupApps.py which automatically zips up a Lambda package for each function and deploys it to AWS Lambda.  Use it whenever you change your code.  The configuration is in `setupconfig.json`.  AWS Lambda configuration options include Lambda name, handler, and memory size.
Modify function configurations (the "functions" array data objects) to add functions or to change the list of files to include in the Lambda package that is uploaded.  The `files_and_dirs` object contains a list of strings that identify either Python3 files (with full paths, relative paths, or no path (for files in current directory), or directories that contain Python3 libraries (such as those under .../site-packages/).  Packages are created by placing all files and directories at the top level (root) and recursively including all directories (as required by AWS Lambda).  

Use the included setupconfig.json (defaults) to build all of the Lambdas herein, 
if no changes have been made.  Here is what it looks like (add more or functions as desired):
```
{
        "region": "us-west-2",
        "lambdaMemory": 128,
        "functions": [
            {
                "name": "DBModPy",
                "handler": "dbMod.handler",
                "zip": "dbmodzip.zip",
                "files_and_dirs": [
                    "dbMod/dbMod.py"
                ],
		"patched_botocore_dir": "venv/lib/python3.6/site-packages/botocore",
                "s3bucket": "cjktestbkt"
            }
        ]
}
```

The build/deploy tool (setupApps.py) integrates SpotWrap.  If you don't wish to wrap your Lambdas with loggers, then use the `--no-spotwrap` option to the `setupApps.py` below.
Using this option, you need not need to **create a AWS DynamoDB table called `spotFns`**.

If you do wish to use SpotWrap, make a table n AWS DynamoDB called `spotFns`.
Ensure that it has a primary key called "ts" with type Number and sort key called "requestID" with type String.

See each function below under **Run It** for instructions to invoke each function.

The [aws command line tools](http://docs.aws.amazon.com/cli/latest/userguide/installing.html) must be installed and configured to use your locally-stored credentials. This will work if you prefer to use an AWS profile (details are below)

Setup the project (first time only)
```
#you can/should use the same virtualenv for all three projects
#update setupconfig.json if you add additional python libraries (files or directories)
cd UCSBFaaS-Wrappers/lambda-python
virtualenv venv --python=python3
source venv/bin/activate
pip install --upgrade pip
pip install boto3

#patch botocore: venv/lib/python3.6/site-packages/botocore/client.py with client.patch
cd venv/lib/python3.6/site-packages/botocore
patch -b < ../../../../../client.patch
cd ../../../../..

#run the package tool and deploy the functions to AWS Lambda
#The configuration is in setupconfig.json.
#if you prefer to run this all manually, the steps for doing so are below per function.

#set your AWS Lambda Role (see IAM Management Console / Roles and change XXX and YYY below)
export AWSRole="arn:aws:iam::XXX:role/YYY"
#if you need to create a role, use apps/mr/setup/create-role.py

#create or update AWS Lambda functions as root user
python setupApps.py
#pass in your own json configuration file (must match setupconfig.json format)
python setupApps.py -f myconfig.json
#-OR- create or update AWS Lambda functions using a particular profile name:
python setupApps.py --profile awsprofile1

#if you wish to simply update an existing Lambda function use:
python setupApps.py --profile awsprofile1 --update

#if you wish to delete the functions in AWS Lambda, run this instead:
python setupApps.py --profile awsprofile1 --deleteAll

#If you don't wish to wrap your Lambdas with loggers (SpotWrap), then use:
python setupApps.py --profile awsprofile1 --no-spotwrap
```
**Troubleshooting**  
   If you get this error ```botocore.exceptions.ClientError: An error occurred (UnrecognizedClientException) when calling the UpdateFunctionCode operation: The security token included in the request is invalid.```.  Rerun using `--profile awsprofile1` replacing awsprofile1 with your profile.

# SpotTemplate
This code is for an AWS Lambda function in Python3 that can handle different triggers (logs them) and invokes another Lambda function if an ARN for the function is passed in via the "functionName" key in the payload to invoke.

In all of the code/steps below:
   1) change basiclambda to your role name with dynamodb access and Lambda invoke access
   2) change XXXACCCTXXX to your aws accountID
   3) change awsprofile1 to your AIM profile that has Lambda admin access
   4) change XXX and YYY to your full path to the zip file you create in the step below

Make a table if you haven't yet in AWS DynamoDB called `spotFns`.  
Ensure that it has a primary key called "ts" with type Number and sort key called "requestID" with type String

Build the project 
```
cd UCSBFaaS-Wrappers/lambda-python
source venv/bin/activate
zip -r9 spotzip.zip *.py
cd venv/lib/python3.6/site-packages/   #change this if your site-packages is elsewhere under ./venv
zip -ur ../../../../spotzip.zip *
cd ../../../..  #return back to lambda-python dir
```

Create the AWS Lambda (note handler format (single period) is different from that for a Java AWS Lambda)
```
aws lambda create-function --region us-west-2 --function-name SpotTemplatePy --zip-file fileb:///XXX/YYY//UCSBFaaS-Wrappers/lambda-python/spotzip.zip --role arn:aws:iam::XXXACCTXXX:role/basiclambda --handler SpotWrap.handleRequest --runtime python3.6 --profile awsprofile1 --timeout 30 --memory-size 128
# or update (ensure that handler is set to SpotWrap.handleRequest)
aws lambda update-function-code --region us-west-2 --function-name SpotTemplatePy --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-python/spotzip.zip --profile awsprofile1
```

**Run it:**  
```
#logs event (with no function to invoke)
aws lambda invoke --invocation-type Event --function-name SpotTemplatePy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI"}' outputfile
#logs event and invokes function that is passed in
aws lambda invoke --invocation-type Event --function-name SpotTemplatePy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","functionName":"arn:aws:lambda:us-west-2:XXXACCTXXX:function:VALIDFNAME"}' outputfile
```

This function will not invoke itself (if its own ARN is passed in). It will not do anything if no ARN is passed in. Finally, it can handle (log) triggers from 
   1) DynamoDB
   2) S3
   3) Other functions: e.g. from lambda-java for example: `aws lambda invoke --invocation-type Event --function-name FnInvoker --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","functionName":"arn:aws:lambda:us-west-2:XXXACCTXXX:function:SpotTemplatePy"}' outputfile`
   4) SNS
   
# dbMod.py function: DBModPy
Build the project 
```
#this assumes that you have setup the virtualenv for the previous project, activate it
cd UCSBFaaS-Wrappers/lambda-python/
cd dbMod
zip -r9 dbmod.zip *.py
cd ../venv/lib/python3.6/site-packages/ #change this if your site-packages is elsewhere under ./venv
zip -ur ../../../../dbMod/dbmod.zip *
cd ../../../../dbMod  #return back to the dbMod directory
```
We assume here that you have setup your spotFns table in DynamoDB (see above for the details on setting this up).
Perform the same setup as for SpotTemplatePy above and create your Lambda wrapped with SpotWrap:
```
aws lambda create-function --region us-west-2 --function-name DBModPy --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-python/dbMod/dbmod.zip --role arn:aws:iam::XXXACCTXXX:role/basiclambda --handler SpotWrap.handleRequest --runtime python3.6 --profile awsprofile1 --timeout 30 --memory-size 128  
# or update (ensure that handler is set to SpotWrap.handleRequest)
aws lambda update-function-code --region us-west-2 --function-name DBModPy --zip-file fileb:///XXX/YYY/RESEARCH/lambda/UCSBFaaS-Wrappers/lambda-python/dbMod/dbmod.zip --profile awsprofile1
```

**Run it:**  
Use the following ("mykey" must be a new key to the table for the trigger to work, if trigger was created as an insert/update trigger):
```
aws lambda invoke --invocation-type Event --function-name DBModPy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","mykey":"newkey2","myval":"100"}' outputfile
```
The function assumes a DynamoDB table in the same region that is called triggerTable (with a primary key called "name" of type String and no Sort Key).  Link this table (as a trigger) to a different Lambda function (e.g. SpotTemplate.{py,java}) to have SpotWrap capture the dependency across services.

# s3mod function S3ModPy
Build the project 
```
#this assumes that you have setup the virtualenv for the previous project, activate it
cd UCSBFaaS-Wrappers/lambda-python/s3Mod
cd s3Mod
zip -r9 s3mod.zip *.py
cd ../venv/lib/python3.6/site-packages/ #change this if your site-packages is elsewhere under ./venv
zip -ur ../../../../s3Mod/s3mod.zip *
cd ../../../../s3Mod  #return back to the s3Mod directory
```
We assume here that you have setup your spotFns table in DynamoDB (see above for the details on setting this up).
Perform the same setup as for SpotTemplatePy above and create your Lambda wrapped with SpotWrap:
```
aws lambda create-function --region us-west-2 --function-name S3ModPy --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-python/s3Mod/s3mod.zip --profile awsprofile1 --timeout 30 --memory-size 128 --role arn:aws:iam::XXXACCTXXX:role/basiclambda --handler SpotWrap.handleRequest --runtime python3.6
# or update (ensure that handler is set to SpotWrap.handleRequest)
aws lambda update-function-code --region us-west-2 --function-name S3ModPy --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-python/s3Mod/s3mod.zip --profile awsprofile1
```

**Run it:**  
Create a bucket in s3 and use it to run this function, adding the prefix (e.g. PythonLambda for SpotTemplatePy and JavaLambda for SpotTemplate) so that updates will trigger your other function, e.g. SpotWrap.  keys bkt, prefix, fname, and file_content are required or this function does nothing.  eventSource tells SpotWrap that you are calling S3ModPy from the CLI externally:
```
aws lambda invoke --invocation-type Event --function-name S3ModPy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","bkt":"cjklambdatrigger","prefix":"PythonLambda","fname":"todo.txt","file_content":"get groceries"}' outputfile
```
# sns function SNSPy
Build the project 
```
#this assumes that you have setup the virtualenv for the previous project, activate it
cd UCSBFaaS-Wrappers/lambda-python
cd sns
zip -r9 sns.zip *.py
cd ../venv/lib/python3.6/site-packages/ #change this if your site-packages is elsewhere under ./venv
zip -ur ../../../../sns/sns.zip *
cd ../../../../sns  #return back to the sns directory
```
We assume here that you have setup your spotFns table in DynamoDB (see above for the details on setting this up).
Perform the same setup as for SpotTemplatePy above and create your Lambda wrapped with SpotWrap:
```
aws lambda create-function --region us-west-2 --function-name SNSPy --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-python/sns/sns.zip --profile awsprofile1 --timeout 30 --memory-size 128 --role arn:aws:iam::XXXACCTXXX:role/basiclambda --handler SpotWrap.handleRequest --runtime python3.6
# or update (ensure that handler is set to SpotWrap.handleRequest)
aws lambda update-function-code --region us-west-2 --function-name SNSPy --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-python/sns/sns.zip --profile awsprofile1
```

Create an SNS topic via the AWS Management console and subscribe to it (e.g. via email so that you can confirm the posting).  To add an SNS trigger to one of your AWS Lambda functions (e.g. SpotTemplate), use the console to subscribe your Lambda function to it. If you use the `add trigger` option in the AWS Lambda console for your function, you will only be able to add SNS topics in the same region as a trigger (so its better to use subscribe from the SNS console).  **Note** that an AWS Lambda function can only post to an SNS topic it its own region.

Use the ARN of the topic in the invoke call below (TOPIC_ARN -- which can be found on the SNS Management Console next to your topic (make sure you are in the right region (notifications in one region can trigger Lambda functions in different regions)).  eventSource tells SpotWrap that you are calling SNSPy from the CLI externally:

**Run It**
```
aws lambda invoke --invocation-type Event --function-name SNSPy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","topic":"TOPIC_ARN","subject":"any subject","msg":"any message"}' outputfile

#see subscription details given a particular subscription ARN from SNS Mgmnt Console:
aws sns get-subscription-attributes --subscription-arn arn:aws:sns:us-west-2:XXX:TOPICNAME:YYY --profile awsprofile1
#see topic details given a particular topic ARN from SNS Mgmnt Console:
aws sns get-topic-attributes --topic-arn arn:aws:sns:us-west-2:XXX:TOPICNAME --profile awsprofile1
```

# FnInvoker.py function FnInvokerPy
Build this with setupApps to place in AWS Lambda.  Otherwise you can just run it from the command line:
**Run It**
```
python FnInvoker.py "arn:aws:lambda:us-west-2:XXXACCTXXX:function:DBModPy" ext:invokeCLI --count 1
```
