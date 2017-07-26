# SpotTemplate
This code is for an AWS Lambda function in Python3 that can handle different triggers (logs them) and invokes another lambda function if an ARN for the function is passed in via the "functionName" key in the payload to invoke.

Setup the project (first time only)
```
cd UCSBFaaS-Wrappers/lambda-python
virtualenv venv --python=python3
source venv/bin/activate
pip install --upgrade pip
pip install boto3 jsonpickle datetime
```
In all of the code/steps below:
   1) change basiclambda to your role name with dynamodb access and lambda invoke access
   2) change XXXACCCTXXX to your aws accountID
   3) change awsprofile1 to your AIM profile that has lambda admin access
   4) change XXX and YYY to your full path to the zip file you create in the step below

Make a table if you haven't yet in AWS DynamoDB called `spotFnTable`  
Ensure that it has a primary key called "requestID" with type String and sort key called "start" with type String

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

Run it:
```
#logs event (with no function to invoke)
aws lambda invoke --invocation-type Event --function-name SpotTemplatePy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI"}' outputfile
#logs event and invoke function passed in
aws lambda invoke --invocation-type Event --function-name SpotTemplatePy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","functionName":"arn:aws:lambda:us-west-2:XXXACCTXXX:function:VALIDFNAME"}' outputfile
```

This function will not invoke itself (if its own ARN is passed in), will not do anything if no ARN is passed in, and can handle (log) triggers from 
   1) DynamoDB
   2) S3
   3) Other functions: e.g. from lambda-java for example: `aws lambda invoke --invocation-type Event --function-name FnInvoker --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","functionName":"arn:aws:lambda:us-west-2:XXXACCTXXX:function:SpotTemplatePy"}' outputfile`
   
# dbMod.py function: DBModPy
Build the project 
```
cd UCSBFaaS-Wrappers/lambda-python/dbMod
#first time only
virtualenv venv --python=python3
source venv/bin/activate
pip install --upgrade pip
pip install boto3 jsonpickle datetime

#patch botocore: venv/lib/python3.6/site-packages/botocore/client.py
#WARNING these next two steps have not been tested yet!
cd venv/lib/python3.6/site-packages/botocore
patch -b -p4 < ../../../../../UCSBFaaS-Wrappers/lambda-python/client.patch

#everytime
zip -r9 dbmod.zip *.py
cd venv/lib/python3.6/site-packages/   #change this if your site-packages is elsewhere under ./venv
zip -ur ../../../../dbmod.zip *
cd ../../../..  #return back to lambda-python dir
```
Perform the same setup as for SpotTemplatePy above and create your lambda wrapped with SpotWrap:
```
aws lambda create-function --region us-west-2 --function-name DBModPy --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-python/dbMod/dbmod.zip --role arn:aws:iam::XXXACCTXXX:role/basiclambda --handler SpotWrap.handleRequest --runtime python3.6 --profile awsprofile1 --timeout 30 --memory-size 128  
# or update (ensure that handler is set to SpotWrap.handleRequest)
aws lambda update-function-code --region us-west-2 --function-name DBModPy --zip-file fileb:///XXX/YYY/RESEARCH/lambda/UCSBFaaS-Wrappers/lambda-python/dbMod/dbmod.zip --profile awsprofile1
```
Run it via the following ("mykey" must be a new key to the table for the trigger to work, if trigger was created as an insert/update trigger):
```
aws lambda invoke --invocation-type Event --function-name DBModPy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","mykey":"newkey2","myval":"100"}' outputfile
```
The function assumes a DynamoDB table in the same region that is called triggerTable.  Link this table (as a trigger) to a different lambda function (e.g. SpotTemplate.{py,java}) to have SpotWrap capture the dependency across services.

# s3mod function S3ModPy
Build the project 
```
cd UCSBFaaS-Wrappers/lambda-python/s3Mod
#first time only
virtualenv venv --python=python3
source venv/bin/activate
pip install --upgrade pip
pip install boto3 jsonpickle datetime

#everytime
zip -r9 s3mod.zip *.py
cd venv/lib/python3.6/site-packages/   #change this if your site-packages is elsewhere under ./venv
zip -ur ../../../../s3mod.zip *
cd ../../../..  #return back to lambda-python dir
```
Perform the same setup as for SpotTemplatePy above and create your lambda wrapped with SpotWrap:
```
aws lambda create-function --region us-west-2 --function-name S3ModPy --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-python/s3Mod/s3mod.zip --profile awsprofile1 --timeout 30 --memory-size 128 --role arn:aws:iam::XXXACCTXXX:role/basiclambda --handler SpotWrap.handleRequest --runtime python3.6
# or update (ensure that handler is set to SpotWrap.handleRequest)
aws lambda update-function-code --region us-west-2 --function-name S3ModPy --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-python/s3Mod/s3mod.zip --profile awsprofile1
```

Create a bucket in s3 and use it to run this function, adding the prefix (e.g. PythonLambda for SpotTemplatePy and JavaLambda for SpotTemplate) so that updates will trigger your other function, e.g. SpotWrap.  keys bkt, prefix, fname, and file_content are required or this function does nothing.  eventSource tells SpotWrap that you are calling S3ModPy from the CLI externally:
```
aws lambda invoke --invocation-type Event --function-name S3ModPy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","bkt":"cjklambdatrigger","prefix":"PythonLambda","fname":"todo.txt","file_content":"get groceries"}' outputfile
```
