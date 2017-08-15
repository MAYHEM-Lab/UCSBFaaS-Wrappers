## AWS Lambda FaaS Wrappers and Tools

SpotWrap is a tool (for Java and Python) that wraps your AWS Lambda functions in code that logs details about your function before and after its invocation in a DynamoDB table.  The example lambda functions provided herein are called SpotTemplate.java and SpotTemplate.py, for each language respectively.  You can swap these out for your functions to wrap them via SpotWrap.  Details are provided at the language-specific links below.  The setup belows provides details on the DynamoDB table you must setup.

SpotWrap records the caller and callee (when inferable) of your functions.  To enable this, setup some triggers to your function via the steps below.  

Note that everything here is assumed to be (and has been tested for) in a single region: us-west-2

Setup:  
1) Table for SpotWrap records (log).  
Create an AWS dynamoDB table called spotFns (hard coded in SpotWrap.py and SpotWrap.java), setup with primary/partition key called requestID (of type String). SpotWrap (java and python versions) will write its event log to this table.  Set up autoscaling and throughput of 5 reads and 10 writes as minima.
2) Create and upload your lambda functions to AWS (see links below for Java and/or Python)
3) Create AWS SNS notification to trigger lambda your functions wrapped with SpotWrap via the AWS SNS console (https://console.aws.amazon.com/sns/v2/home?region=us-east-1#/topics).  Set this as an event trigger in the AWS Lambda console (https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions?display=list) for each function you want to trigger.
4) Create AWS DynamoDB table with stream to trigger lambda your functions wrapped with SpotWrap.  Create a table with a stream that provides New and Old images as view type via the DynamoDB console.  Set this as an event trigger in the AWS Lambda console (https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions?display=list) for each function you want to trigger.
5) Create a bucket in S3 and add a notification Event (Properties/Events) to trigger a lambda function for all Object Creates for a specific prefix (use a different prefix per lambda function as only one can be called per unique event).
6) Setup AWS API Manager (Gateway) for the functions in the same region (https://us-west-2.console.aws.amazon.com/apigateway/home?region=us-west-2#/apis; create API; add a POST resource with integration type ```AWS Service``` and specify a HTTP Header key-value pair (under IntegrationRequest) with name set to ```X-Amz-Invocation-Type``` and value (Mapped from): ```'Event'``` for asynchronous execution.  Use path override: ```/2015-03-31/functions/arn:aws:lambda:us-west-2:XXXACCTXXX:function:FUNCTION_NAME/invocations``` updating XXXACCTXXX with your account id, FUNCTION_NAME to the name of the AWS Lambda function you wish to trigger, and update the region (us-west-2) if needed.  Trigger the function once deployed via the URL given on the triggers tab. Invoke it via awscurl (https://github.com/okigan/awscurl: ```awscurl --region us-west-2 --profile aws_profile --service execute-api -X POST -d @request.json URL``` with the payload in file request.json).
7) Use the functions under lambda-python as examples/tools to trigger various events:  FnInvoker.py to invoke a lambda function from a lambda function, s3Mod.py to write to your S3 bucket/prefix, and dbMod.py to write/update a dynamodb table, and sns.py to post a notification. The application under mr is a mapreduce job.  The directory lambda-java is incomplete and under construction.

Please see this readme for the Python tools: https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/tree/master/lambda-python

Please see this readme for the Java tools: https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/tree/master/lambda-java


