#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
MRBKT=mr-bucket-0816 #must match reducerCoordinator "permission" in setupconfig-noSpot.json when setupApps.py is run with --no_spotwrap
JOBID=job4000 #must match reducerCoordinator "job_id" in setupconfig-noSpot.json when setupApps.py is run with --no_spotwrap
MRBKTNS=mr-bucket-0816-no #must match reducerCoordinator "permission" in setupconfig-noSpot.json when setupApps.py is run with --no_spotwrap
JOBIDNS=job4001 #must match reducerCoordinator "job_id" in setupconfig-noSpot.json when setupApps.py is run with --no_spotwrap
PREFIX=/Users/fasthall/Workspace/chandra/UCSBFaaS-Wrappers
LAMDIR=${PREFIX}/lambda-python
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/lambda-python/mr
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
TS=1401861965497 #some early date
REG=us-west-2 #some early date

S3TESTBKT=spotwraptest0831
EMP=empty
EMPNS=emptyNS
DBR=dbread
DBRNS=dbreadNS
DBW=dbwrite
DBWNS=dbwriteNS
S3R=s3read
S3RNS=s3readNS
S3W=s3write
S3WNS=s3writeNS
SNS=pubsns
SNSNS=pubsnsNS

cd ${LAMDIR}
. ./venv/bin/activate
cd ${CWDIR}
python downloadLogs.py "/aws/lambda/${EMP}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${DBR}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${DBW}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${S3R}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${S3W}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${SNS}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${EMPNS}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${DBRNS}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${DBWNS}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${S3RNS}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${S3WNS}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${SNSNS}" ${TS} -p ${PROF} --deleteOnly
deactivate

for i in `seq 1 100`;
do
    aws s3 rm s3://${S3TESTBKT}/write --recursive --profile ${PROF}
    #delete the bucket contents for the job
    cd ${LAMDIR}
    . ./venv/bin/activate
    
    # echo "Empty function invocation..."
    aws lambda invoke --invocation-type Event --function-name ${EMPNS} --region ${REG} --profile ${PROF} --payload "{}" outputfile
    echo "DynamoDB function invocation..."
    aws lambda invoke --invocation-type Event --function-name ${DBRNS} --region ${REG} --profile ${PROF} --payload "{}" outputfile
    aws lambda invoke --invocation-type Event --function-name ${DBWNS} --region ${REG} --profile ${PROF} --payload "{}" outputfile
    echo "S3 function invocation..."
    aws lambda invoke --invocation-type Event --function-name ${S3RNS} --region ${REG} --profile ${PROF} --payload "{}" outputfile
    aws lambda invoke --invocation-type Event --function-name ${S3WNS} --region ${REG} --profile ${PROF} --payload "{}" outputfile
    echo "SNS function invocation..."
    aws lambda invoke --invocation-type Event --function-name ${SNSNS} --region ${REG} --profile ${PROF} --payload "{}" outputfile
    
    /bin/sleep 15 #seconds

    #download cloudwatch logs (and delete them)
    cd ${CWDIR}
    mkdir -p $i/APIS/NS/OFF
    python downloadLogs.py "/aws/lambda/${EMPNS}" ${TS} -p ${PROF} --delete > $i/APIS/NS/emp.log
    python downloadLogs.py "/aws/lambda/${DBRNS}" ${TS} -p ${PROF} --delete > $i/APIS/NS/dbread.log
    python downloadLogs.py "/aws/lambda/${DBWNS}" ${TS} -p ${PROF} --delete > $i/APIS/NS/dbwrite.log
    python downloadLogs.py "/aws/lambda/${S3RNS}" ${TS} -p ${PROF} --delete > $i/APIS/NS/s3read.log
    python downloadLogs.py "/aws/lambda/${S3WNS}" ${TS} -p ${PROF} --delete > $i/APIS/NS/s3write.log
    python downloadLogs.py "/aws/lambda/${SNSNS}" ${TS} -p ${PROF} --delete > $i/APIS/NS/pubsns.log
    deactivate    
done

# for i in `seq 1 100`;
# do
#     aws s3 rm s3://${S3TESTBKT}/write --recursive --profile ${PROF}
#     #delete the bucket contents for the job
#     cd ${LAMDIR}
#     . ./venv/bin/activate
    
#     # echo "Empty function invocation..."
#     aws lambda invoke --invocation-type Event --function-name ${EMP} --region ${REG} --profile ${PROF} --payload "{}" outputfile
#     echo "DynamoDB function invocation..."
#     aws lambda invoke --invocation-type Event --function-name ${DBR} --region ${REG} --profile ${PROF} --payload "{}" outputfile
#     aws lambda invoke --invocation-type Event --function-name ${DBW} --region ${REG} --profile ${PROF} --payload "{}" outputfile
#     echo "S3 function invocation..."
#     aws lambda invoke --invocation-type Event --function-name ${S3R} --region ${REG} --profile ${PROF} --payload "{}" outputfile
#     aws lambda invoke --invocation-type Event --function-name ${S3W} --region ${REG} --profile ${PROF} --payload "{}" outputfile
#     echo "SNS function invocation..."
#     aws lambda invoke --invocation-type Event --function-name ${SNS} --region ${REG} --profile ${PROF} --payload "{}" outputfile
    
#     /bin/sleep 90 #seconds

#     #download cloudwatch logs (and delete them)
#     cd ${CWDIR}
#     python downloadLogs.py "/aws/lambda/${EMP}" ${TS} -p ${PROF} --delete > $i/APIS/emp.log
#     python downloadLogs.py "/aws/lambda/${DBR}" ${TS} -p ${PROF} --delete > $i/APIS/dbread.log
#     python downloadLogs.py "/aws/lambda/${DBW}" ${TS} -p ${PROF} --delete > $i/APIS/dbwrite.log
#     python downloadLogs.py "/aws/lambda/${S3R}" ${TS} -p ${PROF} --delete > $i/APIS/s3read.log
#     python downloadLogs.py "/aws/lambda/${S3W}" ${TS} -p ${PROF} --delete > $i/APIS/s3write.log
#     python downloadLogs.py "/aws/lambda/${SNS}" ${TS} -p ${PROF} --delete > $i/APIS/pubsns.log
#     deactivate

#     /bin/sleep 90 #seconds
# done

cd ${TOOLSDIR}
../cleanupAWS.sh ${PROF}