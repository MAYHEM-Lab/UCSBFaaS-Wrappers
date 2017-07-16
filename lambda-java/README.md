# SpotTemplate
* Build the source, we assume here that you are using package `ucsbspot`
```
cd UCSBFaaS-Wrappers/lambda-java/spot
gradle build
```

* Setup.  In all of the code/steps below:  
   1) change basiclambda to your role name with dynamodb access and lambda invoke access
   2) change XXXACCCTXXX to your aws accountID
   3) change awsprofile1 to your AIM profile that has lambda admin access
   4) change XXX and YYY to your full path to the repo directory

* Create the function
```
aws lambda create-function --region us-west-2 --function-name SpotTemplate --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-java/spot/build/distributions/spot.zip --role arn:aws:iam::XXXACCTXXX:role/basiclambda --handler ucsbspot.SpotWrap::handleRequest --runtime java8 --profile awsprofile1 --timeout 30 --memory-size 512
```

* Make a table if you haven't yet in AWS DynamoDB called `spotFnTable`  
Ensure that it has a primary key called "requestID" with type String and sort key called "start" with type String

* Invoke the function  
```
#log invocation from the console/CLI  
aws lambda invoke --invocation-type Event --function-name SpotTemplate --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI"}' outputfile      
```

* This function can also handle being invoked (and will log any such event details) from the following triggers
   DynamoDB
   S3
   lambda function invocation (try using FnInvoker below via `aws lambda invoke --invocation-type Event --function-name FnInvoker --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","functionName":"arn:aws:lambda:us-west-2:443592014519:function:SpotTemplate"}' outputfile`)
   


# FnInvoker
* Build the source, we assume here that you are using package `ucsbspot`
```
cd UCSBFaaS-Wrappers/lambda-java/invoker
gradle build
```

* Setup.  In all of the code/steps below:  
   1) change basiclambda to your role name with dynamodb access and lambda invoke access
   2) change XXXACCCTXXX to your aws accountID
   3) change awsprofile1 to your AIM profile that has lambda admin access
   4) change XXX and YYY to your full path to the repo directory

* Create the function
```
aws lambda create-function --region us-west-2 --function-name FnInvoker --zip-file fileb:///XXX/YYY/UCSBFaaS-Wrappers/lambda-java/invoker/build/distributions/invoker.zip --role arn:aws:iam::XXXACCTXXX:role/basiclambda --handler ucsbspot.SpotWrap::handleRequest --runtime java8 --profile awsprofile1 --timeout 30 --memory-size 512
```

* Make a table if you haven't yet in AWS DynamoDB called `spotFnTable`  
Ensure that it has a primary key called "requestID" with type String and sort key called "start" with type String

* Invoke the function  
```
#call arn passed in (replace XXXARNXXX with full arn of any aws lambda function)  
#ensure that it doesn't call this function (causing infinite loop)
aws lambda invoke --invocation-type Event --function-name FnInvoker --region us-west-2 --profile cjk1 --payload '{"functionName":"XXXARNXXX","eventSource":"ext:invokeCLI"}' outputfile      

#call self recursively once (flags are in place to stop recursion)
aws lambda invoke --invocation-type Event --function-name FnInvoker --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI"}' outputfile      

#call nothing (passed in same arn)
aws lambda invoke --invocation-type Event --function-name FnInvoker --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","functionName":"XXX"}' outputfile
```
