#! /bin/bash

#delete s3 entries for map/reduce jobs
aws s3 rm s3://spot-mr-bkt/job3000 --recursive --profile cjk1
aws s3 rm s3://spot-mr-bkt-ns/jobNS300 --recursive --profile cjk1
#delete dynamodb entries in table spotFns
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/dynamodb
. venv/bin/activate
python dynamodelete.py -p cjk1 spotFns
deactivate
#delete the logs for the lambdas with spotwrap and without (NS)
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/lambda-python/mr
. ../venv/bin/activate
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/cloudwatch
python downloadLogs.py "/aws/lambda/mapper" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/reducer" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/driver" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinator" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/mapperNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/reducerNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/driverNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinatorNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/SNSPy" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/S3ModPy" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/DBModPy" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/FnInvokerPy" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/SpotTemplatePy" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/SNSPyNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/S3ModPyNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/DBModPyNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/FnInvokerPyNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/SpotTemplatePyNS" 1401861965497 -p cjk1 --deleteOnly
deactivate

#cleanup mapreduce job output
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/lambda-python/mr
rm -f 1/overhead.out 2/overhead.out 3/overhead.out 4/overhead.out 5/overhead.out 6/overhead.out 7/overhead.out 8/overhead.out 9/overhead.out 10/overhead.out
rm -f 1/NS/overhead.out 2/NS/overhead.out 3/NS/overhead.out 4/NS/overhead.out 5/NS/overhead.out 6/NS/overhead.out 7/NS/overhead.out 8/NS/overhead.out 9/NS/overhead.out 10/NS/overhead.out
#cleanup mapreduce job output: cloudwatch downloads
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/cloudwatch
rm -f 1/*.log 1/NS/*.log 2/*.log 2/NS/*.log 3/*.log 3/NS/*.log 4/*.log 4/NS/*.log 5/*.log 5/NS/*.log 6/*.log 6/NS/*.log 7/*.log 7/NS/*.log 8/*.log 8/NS/*.log 9/*.log 9/NS/*.log 10/*.log 10/NS/*.log
#cleanup mapreduce job output: cloudwatch downloads
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/dynamodb
rm -f 1/dump 1/NS/dump 2/dump 2/NS/dump 3/dump 3/NS/dump 4/dump 4/NS/dump 5/dump 5/NS/dump 6/dump 6/NS/dump 7/dump 7/NS/dump 8/dump 8/NS/dump 9/dump 9/NS/dump 10/dump 10/NS/dump
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools

