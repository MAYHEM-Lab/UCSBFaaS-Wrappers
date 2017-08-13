# Tools to collect timings with and without spotwrap

Pass into each bash script your AWS account ID and your AWS profile, e.g. ```./mr.sh 1401861965497 awsprofile1```. The large valued argument is an early timestamp (epoch milliseconds). This is the timestamp to go back to when looking for cloudwatch records.

**cleanup.sh** deletes all files, logs, database entries, and all outputs from overhead.sh and overheadNS.sh.  Use this with caution.  You may need to run this multiple times until all of the running jobs complete and write out their data and logs (e.g. if you stopped/killed a job midstream!)... until you see ```Table 'spotFns' is empty.``` repeatedly, keep retrying after some time delay.   
**cleanupAWS.sh** does the same except it does NOT delete overhead.sh and overheadNS.sh output files

**overhead.sh** runs the map/reduce job with SpotWrap support 10 times and collects the results in lambda-python/mr/{1..10}, tools/cloudwatch/{1..10}, and tools/dynamodb/{1..10}.  This job assumes that the lambda names are mapper, reducer, reducerCoordinator, and driver (set in setupconfig.json for setupApps.py installation).

**overheadNS.sh** runs the map/reduce job without SpotWrap support 10 times and collects the results in lambda-python/mr/{1..10}, tools/cloudwatch/{1..10}, and tools/dynamodb/{1..10}.  This job assumes that the lambda names are mapperNS, reducerNS, reducerCoordinatorNS, and driverNS (set in setupconfig.json for setupApps.py installation).

**mr.sh** runs the SpotWrap map-reduce job in lambda and collects its output data from cloudwatch and the database. It also executes the various other apps that are part of the lambda-python benchmark set (SNS, S3, DynamoDB, and API Invoke triggers).


# Example use and setup
```
#set your environment
#update the prefix below with yours to the UCSBFaas-Wrappers directory
export PREFIX=/my/path/to/UCSBFaaS-Wrappers
cd ${PREFIX}/lambda-python
source venv/bin/activate

#delete everything in AWS and locally
cd ${PREFIX}/tools/timings
./cleanup.sh aws_profile

#generate the base log file if you don't have one (stream starting point), replace the arn with your STREAM arn for the spot functions table in dynamodb (dyndb management console)
cd .. 
python get_stream_data.py STREAM_ARN -p aws_profile >& new_stream
sort -n -k 1 new_stream |awk 'NF' > spotFn.stream.base

#cleanup cloudwatch logs
cd ../../lambda-python
deactivate; source venv/bin/activate
#set your AWS Lambda Role (see IAM Management Console / Roles and change XXX and YYY below)
#if you need to create a role, use apps/mr/setup/create-role.py
export AWSRole=arn:aws:iam::AWS_ACCT:role/AWS_INVOKE_LAMBDA_ROLE 

python setupApps.py --profile aws_profile --deleteAll -f scns.json
python setupApps.py --profile aws_profile --deleteAll -f scns-noSpot.json
python setupApps.py --profile aws_profile --deleteAll -f setupconfig-noSpot.json
python setupApps.py --profile aws_profile --deleteAll 

#deploy apps: scns is mapreduce, setupconfig are the others (invoke,sns,db,s3 drivers)
#edit scns.json and scns-noSpot.json to change job_id if you want entirely new ones for each
python setupApps.py --profile aws_profile 

#You don't need to regenerate the zip library for the others, since the above does so and stores in S3 
python setupApps.py -f scns.json --no_botocore_change --profile aws_profile
#use --no_spotwrap for the noSpot configurations
python setupApps.py -f scns-noSpot.json --no_botocore_change --no_spotwrap --profile aws_profile
python setupApps.py -f setupconfig-noSpot.json --no_botocore_change --no_spotwrap --profile aws_profile

############################################################
#run apps: collect data for overhead comparison with and without spotwrap (NS)
cd ${PREFIX}/tools/timings
deactivate
./overhead.sh aws_profile
./overheadNS.sh aws_profile

#process the output files 
cd ${PREFIX}/lambda-python
source venv/bin/activate

#process the overhead timings
cd ../tools
python timings_parser.py ${PREFIX}/lambda-python/mr ${PREFIX}/tools/cloudwatch ${PREFIX}/tools/dynamodb tmp.out

Example:
(venv) cjkmobile:tools ckrintz$ python timings_parser.py ${PREFIX}/lambda-python/mr ${PREFIX}/tools/cloudwatch ${PREFIX}/tools/dynamodb tmp.out
JOB: BOTH
NStotal:10,map_avg:92.43821298665014:map_stdev:10.481580849877783:map_count:29:dsize:26186978239.0:keys:202
SPOTtotal:10,map_avg:94.52861484823556:map_stdev:10.937622376671214:map_count:29:dsize:26186978239.0:keys:202

############################################################
#run apps: collect data for dependency analysis
cd ${PREFIX}/tools/timings
deactivate
#modify mr.sh to update JOBID and JOBIDNS to match the new job_id values if you changed them
./mr.sh aws_profile

#output files:
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/cloudwatch
see 1/MR/map.log,red.log,driv.log,coord.log


#generate the dependencies and total ordering (replace STREAM_ARN and aws_profile
python get_stream_data.py STREAM_ARN -p aws_profile | sort -n -k 1 >  new_stream
#append new_stream entries to base
diff -b -B spotFn.stream.base new_stream | awk -F"> " '{print $2}' | awk 'NF' > grot
cat grot >> spotFn.stream.base

#process the entries since the last call to cleanup
python ddb_parser.py spotFn.stream.base
#see spotgraph.pdf for graph and stdout for total order

#run this instead to process the entire file
	python ddb_parser.py spotFn.stream.base --process_entire_file

#either of the above produces spotgraph.pdf in this directory (red nodes indicate errors); 
#node names in graph are as follows
#for parent-less nodes (duration in msecs):  
	request_type:name_and_req_ID:seq  
	seq:sequence_range,dur:duration ms
#for child nodes (duration in msecs):
	request_type:name_and_req_ID:seq
	dur:duration
#if child nodes are internal triggers (eg S3 or DB writes), then 
#duration is instead the time between the entry and this trigger (prefixed by b4)
#and the time between this and the exit (prefixed by af)

#std out contains total order of sequence numbers and any events which did not trigger other lambdas
```

**Please NOTE:**   
The map-reduce output can differ across runs because the coordinator may invoke
the reducer multiple times (depending upon when it is triggered by mapper writes and when
all mappers complete).  This will cause differences in the output.

