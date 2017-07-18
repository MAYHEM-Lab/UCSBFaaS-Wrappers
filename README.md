## AWS Lambda FaaS Wrappers and Tools

The example lambda functions provided herein are called SpotTemplate.java and SpotTemplate.py, for each language respectively.

Setup:  
1) Table for SpotWrap records (log).  
Create an AWS dynamoDB table called spotFns (hard coded in SpotWrap.py and SpotWrap.java), setup with primary/partition key called ts (Number) and sort key called requestID (String). Set this as your trigger for either your Java function or Python function (or both) that is wrapped with SpotWrap, e.g. SpotTemplate.  
2) Create and upload your lambda functions to AWS (see links below for Java and/or Python)
3) Create AWS SNS notification to trigger lambda your functions wrapped with SpotWrap via the AWS SNS console (https://console.aws.amazon.com/sns/v2/home?region=us-east-1#/topics).  Set this as an event trigger in the AWS Lambda console (https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions?display=list) for each function you want to trigger.
4) Create AWS DynamoDB table with stream to trigger lambda your functions wrapped with SpotWrap.  Create a table with a stream that provides New and Old images as view type via the DynamoDB console.  Set this as an event trigger in the AWS Lambda console (https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions?display=list) for each function you want to trigger.
5) Create a bucket in S3 and add a notification Event (Properties/Events) to trigger a lambda function for all Object Creates for a specific prefix (use a different prefix per lambda function as only one can be called per unique event).
6) use these functions as examples/tools to trigger various events:  FnInvoker (java) to invoke a lambda function from a lambda function (lambda-java), s3Mod.py (lambda-python) to write to your S3 bucket/prefix, and dbMod.py (lambda-python) to write/update a dynamodb table.

Please see this readme for the Java tools: https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/tree/master/lambda-java

Please see this readme for the Python tools: https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/tree/master/lambda-python

