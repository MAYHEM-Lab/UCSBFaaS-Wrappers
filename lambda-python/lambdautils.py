'''
 From: https://github.com/awslabs/lambda-refarch-mapreduce
 Modifications fall under ../LICENSE
 * LICENSE for original file:
 * Copyright 2016, Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Amazon Software License (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 *
 * http://aws.amazon.com/asl/
 *
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License. 
'''
import boto3,botocore,os,sys

class LambdaManager(object):
    def __init__ (self, l, region, codepath, fname, handler, tracing=False, lmem=1536):
        self.awslambda = l;
        self.region = "us-east-1" if region is None else region
        self.codefile = codepath
        self.function_name = fname
        self.handler = handler
        self.memory = lmem 
        self.timeout = 300
        self.role = os.environ.get('AWSRole')
        if not self.role:
            print('Please set AWSRole in your environment variables to your AWS Lambda Role')
            sys.exit(1)
        self.tracing = tracing # if true, turn on Xray tracing (not needed with SpotWrap)
        self.function_arn = None # set after creation

    def create_lambda_function(self):
        runtime = 'python3.6'
        response = self.awslambda.create_function(
                      FunctionName = self.function_name, 
                      Code = { 
                        "ZipFile": open(self.codefile, 'rb').read()
                      },
                      Handler =  self.handler,
                      Role =  self.role, 
                      Runtime = runtime,
                      Description = self.function_name,
                      MemorySize = self.memory,
                      Timeout =  self.timeout,
                      TracingConfig =  {'Mode':'Active'} if self.tracing else {'Mode':'PassThrough'}
                    )
        self.function_arn = response['FunctionArn']
        print(response)

    def update_function(self):
        '''
        Update lambda function
        '''
        response = self.awslambda.update_function_code(
                FunctionName = self.function_name, 
                ZipFile=open(self.codefile, 'rb').read()
                #Publish=True
                )
        updated_arn = response['FunctionArn']
        # parse arn and remove the release number (:n) 
        #arn = ":".join(updated_arn.split(':')[:-1]) broken when no release number
        arn = updated_arn
        self.function_arn = arn 
        print(response)

    def update_code_or_create_on_noexist(self):
        '''
        Update if the function exists, else create function
        '''
        try:
            self.create_lambda_function()
        except botocore.exceptions.ClientError as e:
            # parse (Function already exist) 
            self.update_function()

    def add_lambda_permission(self, sId, bucket):
        resp = self.awslambda.add_permission(
          Action = 'lambda:InvokeFunction',
          FunctionName = self.function_name,
          Principal = 's3.amazonaws.com',
          StatementId = '%s' % sId,
          SourceArn = 'arn:aws:s3:::' + bucket
        )
        print(resp)

    def create_s3_eventsource_notification(self, s3, bucket, prefix=None):
        if not prefix:
            prefix = self.job_id +"/task";

        s3.put_bucket_notification_configuration(
          Bucket =  bucket,
          NotificationConfiguration = {
            'LambdaFunctionConfigurations': [
              {
                  'Events': [ 's3:ObjectCreated:*'],
                  'LambdaFunctionArn': self.function_arn,
                   'Filter' : {
                    'Key':    {
                        'FilterRules' : [
                      {
                          'Name' : 'prefix',
                          'Value' : prefix
                      },
                    ]
                  }
                }
              }
            ],
            #'TopicConfigurations' : [],
            #'QueueConfigurations' : []
          }
        )
    def delete_function(self):
        self.awslambda.delete_function(FunctionName=self.function_name)

    @classmethod
    def deleteBucketContents(cls, s3, bucketname):
        ''' Delete the contents of s3 bucket named bucketname '''
        b = s3.Bucket(bucketname)
        b.objects.all().delete()

    @classmethod
    def cleanup_logs(cls, func_name):
        '''
        Delete all Lambda log group and log streams for a given function

        '''
        log_client = boto3.client('logs')
        response = log_client.delete_log_group(logGroupName='/aws/lambda/' + func_name)
        return response

    @classmethod
    def copyToS3(cls,s3,bucketname,filename):
        '''
        Copy file to s3 in bucket 
        '''
        fname = os.path.basename(filename)
        return s3.Object(bucketname, fname).upload_file(filename)

    @classmethod
    def S3BktExists(cls,s3,bucketname,region):
        '''
        Check that s3 bucket exists; idempotent so either creates it or does nothing
        '''
        try:
            s3.create_bucket(Bucket=bucketname,CreateBucketConfiguration={'LocationConstraint': region})
        except:
            pass
        return True
        
    @classmethod
    def write_to_s3(cls, s3, bucket, key, data, metadata):
        s3.Bucket(bucket).put_object(Key=key, Body=data, Metadata=metadata)

