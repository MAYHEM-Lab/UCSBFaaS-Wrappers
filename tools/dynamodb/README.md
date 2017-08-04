## dynamodump
Backup a DynamoDB table to the local filesystem.  
From: https://github.com/bchew/dynamodump  
Modifications licensed under https://github.com/MAYHEM-Lab/UCSBFaaS-Wrappers/blob/master/LICENSE   
Usage:  (python2.7, boto, boto3)  
```
python dynamodump.py -m backup -r aws_region -p aws_profile -s TableName
```  
Output is placed in dump/TableName/{data,schema.json} and is in json format.

## dynamodelete
Delete all items from DynamoDB table.  
Usage:  (python2.7, boto, boto3)  
```
#dry run --  just count, but don't delete
python dynamodelete.py -p aws_profile TableName -d

#delete all items in TableName
python dynamodelete.py -p aws_profile TableName
```
