# Tools to collect timings with and without spotwrap


**cleanupAWS.sh** deletes all files, logs, database entries, and all outputs from overhead.sh and overheadNS.sh.  Use this with caution.  You may need to run this multiple times until all of the running jobs complete and write out their data and logs (e.g. if you stopped/killed a job midstream!)... until you see ```Table 'spotFns' is empty.``` repeatedly, keep retrying after some time delay.   Edit to add deletion of local results files (see commented lines at end of file)

**overhead?.sh** runs the map/reduce job for a given number of runs: ```./overheadS.sh aws_profile 10```   
Possible tests (capital letter suffix) are S=static gammaray (original spotwrap)   
C=clean (no gammaray or spotwrap or tracing)   
T=clean with X-ray tracing on   
F=x-ray tracing on and fleece support (x-ray daemon)
G=gammaray support (dynamic gammaray via fleece extensions; x-ray tracing should be turned off)

**mr.sh** runs the SpotWrap map-reduce job in lambda and collects its output data from cloudwatch and the database. It also executes the various other apps that are part of the lambda-python benchmark set (SNS, S3, DynamoDB, and API Invoke triggers).

# Example use and setup
```
#set your environment
#update the prefix below with yours to the UCSBFaas-Wrappers directory
export PREFIX=/my/path/to/UCSBFaaS-Wrappers
cd ${PREFIX}/gammaRay
source venv/bin/activate

run a job: ```./overheadS.sh aws_profile```  (see below ###### for more)

#delete everything in AWS and locally, run multiple times
cd ${PREFIX}/tools/timings
./cleanupAWS.sh aws_profile
./cleanupAWS.sh aws_profile
./cleanupAWS.sh aws_profile

#delete all lambdas
export AWSRole=arn:aws:iam::AWS_ACCT:role/AWS_INVOKE_LAMBDA_ROLE 
python cleanupLambdas.sh aws_profile ${AWSRole}

############################################################
#run apps: collect data for overhead comparison with and without spotwrap (NS)
cd ${PREFIX}/tools/timings
deactivate
./overheadS.sh aws_profile
./overheadC.sh aws_profile

#process the output files 
cd ${PREFIX}/gammaRay
source venv/bin/activate

#generate the base log file if you don't have one (stream starting point), replace the arn with your STREAM arn for the spot functions table (spotFns or gammaRays) in dynamodb (see dynamodb management console)
cd .. 
python get_stream_data.py STREAM_ARN -p aws_profile >& spotFn.stream.base
cd tools

#process the overhead timings
cd ../tools
python timings_parser.py ${PREFIX}/lambda-python/mr ${PREFIX}/tools/cloudwatch tmp.out

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
python get_stream_data.py STREAM_ARN -p aws_profile >  new_stream
#append new_stream entries to base
diff -b -B spotFn.stream.base new_stream | awk -F"> " '{print $2}' | awk 'NF' > grot
cat grot >> spotFn.stream.base

#if you prefer to process just the most recent stream entries, edit get_stream_data.py 
#and set DEBUG to true. Then run   
python get_stream_data.py STREAM_ARN -p aws_profile 
#to see the sequence numbers.  Pick an end sequence number at which you want to stop:
...
SHARD:shardId-00000001502645848152-8747f222:51502500000000023987600700:51643800000000024001872971
#use it on the command line to expedite the stream acquisition process:
python get_stream_data.py STREAM_ARN -p aws_profile --seqid 51643800000000024001872971 >  new_stream
#then process the new data:
python ddb_parser.py new_stream
#see spotgraph.pdf for graph and stdout for total order

#or process the entries since the last call to cleanup, i.e. since last set 
#of REMOVES due to python dynamodelete.py -p ${PROF} ${SPOTTABLE}
python ddb_parser.py spotFn.stream.base
#see spotgraph.pdf for graph and stdout for total order

#run this instead to process the entire file
python ddb_parser.py spotFn.stream.base --process_entire_file
#see spotgraph.pdf for graph and stdout for total order

#ddb_parser produces spotgraph.pdf in this directory (red nodes indicate errors); 
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

#use this instead to also include read events (non-triggers) in output files
python ddb_parser.py spotFn.stream.base --include_reads

#std out contains total order of sequence numbers and any events which did not trigger other lambdas
total order output lines =  A:B:C:D:E:F:G:H   
        A: sequence number in total order
        B: name (includes colons so be careful here)
        C: Names (nm) value (NAMES enum in ddb_parser.py)
        D: duration as reported by exit (entry nodes only)
        E: if D != 0, this is duration as reported by difference in timestamps of start/exit
           if D == 0, this is duration between entry timestamp and this event's timestamp
        F: if D != 0, this is 0
           if D == 0, this is duration between exit timestamp and this event's timestamp
```

**Please NOTE:**   
The map-reduce output can differ across runs because the coordinator may invoke
the reducer multiple times (depending upon when it is triggered by mapper writes and when
all mappers complete).  This will cause differences in the output.

