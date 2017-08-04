#dynamodump
Backup a DynamoDB table to the local filesystem.
From: https://github.com/bchew/dynamodump  
Modifications licensed under https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/blob/master/LICENSE  
Usage:  (python2.7, boto, boto3)
```
python dynamodump.py -m backup -r aws_region -p aws_profile -s TableName
```

#dynamodelete
Delete all items from DynamoDB table.
Usage:  (python2.7, boto, boto3)
```
python dynamodelete.py -p aws_profile TableName
```
