#! /bin/bash
ACCT=XXX
PROF=YYY
MRBKT=spot-mr-bkt #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run without --no_spotwrap
MRBKTNS=spot-mr-bkt-ns #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
JOBID=job3000  #must match reducerCoordinator "job_id" in setupconfig.json when setupApps.py is run without --no_spotwrap
JOBIDNS=jobNS300 #must match reducerCoordinator "job_id" in setupconfig.json when setupApps.py is run with --no_spotwrap
PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
LAMDIR=${PREFIX}/lambda-python
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/lambda-python/mr
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template

cd ${TOOLSDIR}
#delete s3 entries for map/reduce jobs
aws s3 rm s3://${MRBKT}/${JOBID} --recursive --profile ${PROF}
aws s3 rm s3://${MRBKTNS}/${JOBIDNS} --recursive --profile ${PROF}
#delete dynamodb entries in table ${SPOTTABLE}
cd ${DYNDBDIR}
. venv/bin/activate
python dynamodelete.py -p ${PROF} ${SPOTTABLE}
deactivate
#delete the logs for the lambdas with spotwrap and without (NS)
cd ${MRDIR}
. ../venv/bin/activate
cd ${CWDIR}
python downloadLogs.py "/aws/lambda/mapper" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducer" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/driver" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinator" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/mapperNS" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerNS" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/driverNS" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinatorNS" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/SNSPy" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/S3ModPy" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/DBModPy" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/FnInvokerPy" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/SpotTemplatePy" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/SNSPyNS" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/S3ModPyNS" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/DBModPyNS" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/FnInvokerPyNS" ${ACCT} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/SpotTemplatePyNS" ${ACCT} -p ${PROF} --deleteOnly
deactivate

#cleanup mapreduce job output
cd ${MRDIR}
rm -f 1/overhead.out 2/overhead.out 3/overhead.out 4/overhead.out 5/overhead.out 6/overhead.out 7/overhead.out 8/overhead.out 9/overhead.out 10/overhead.out
rm -f 1/NS/overhead.out 2/NS/overhead.out 3/NS/overhead.out 4/NS/overhead.out 5/NS/overhead.out 6/NS/overhead.out 7/NS/overhead.out 8/NS/overhead.out 9/NS/overhead.out 10/NS/overhead.out
#cleanup mapreduce job output: cloudwatch downloads
cd ${CWDIR}
rm -f 1/*.log 1/NS/*.log 2/*.log 2/NS/*.log 3/*.log 3/NS/*.log 4/*.log 4/NS/*.log 5/*.log 5/NS/*.log 6/*.log 6/NS/*.log 7/*.log 7/NS/*.log 8/*.log 8/NS/*.log 9/*.log 9/NS/*.log 10/*.log 10/NS/*.log
#cleanup mapreduce job output: dynamodb downloads
cd ${DYNDBDIR}
rm -rf 1/dump 1/NS/dump 2/dump 2/NS/dump 3/dump 3/NS/dump 4/dump 4/NS/dump 5/dump 5/NS/dump 6/dump 6/NS/dump 7/dump 7/NS/dump 8/dump 8/NS/dump 9/dump 9/NS/dump 10/dump 10/NS/dump
cd ${TOOLSDIR}

