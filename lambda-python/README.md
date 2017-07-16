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

Build the project (update HOMEDIR as appropriate)
```
cd UCSBFaaS-Wrappers/lambda-python
source venv/bin/activate
zip -r9 /HOMEDIR/myzip.zip *.py
cd venv/lib/python3.6/site-packages/   #change this if your site-packages is elsewhere under ./venv
zip -ur /HOMEDIR/myzip.zip *
cd ../../../..  #return back to lambda-python dir
```

Create the AWS Lambda (note handler format (single period) is different from that for a Java AWS Lambda)
```
aws lambda create-function --region us-west-2 --function-name SpotTemplatePy --zip-file fileb:///XXX/YYY/myzip.zip --role arn:aws:iam::XXXACCTXXX:role/basiclambda --handler SpotWrap.handleRequest --runtime python3.6 --profile awsprofile1 --timeout 30 --memory-size 128
```

Run it:
```
#logs event (with no function to invoke)
aws lambda invoke --invocation-type Event --function-name SpotTemplatePy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI"}' outputfile
#logs event and invoke function passed in
aws lambda invoke --invocation-type Event --function-name SpotTemplatePy --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","functionName":"arn:aws:lambda:us-west-2:443592014519:function:VALIDFNAME"}' outputfile
```

This function will not invoke itself (if its own ARN is passed in), will not do anything if no ARN is passed in, and can handle (log) triggers from 
   1) DynamoDB
   2) S3
   3) Other functions: e.g. from lambda-java for example: `aws lambda invoke --invocation-type Event --function-name FnInvoker --region us-west-2 --profile awsprofile1 --payload '{"eventSource":"ext:invokeCLI","functionName":"arn:aws:lambda:us-west-2:XXXACCTXXX:function:SpotTemplatePy"}' outputfile`
