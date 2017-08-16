#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset AWS Account ID. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
ACCT=$2
MRBKT=spot-mr-bkt-ns #must match reducerCoordinator "permission" in setupconfig-noSpot.json when setupApps.py is run with --no_spotwrap
JOBID=jobNS4000 #must match reducerCoordinator "job_id" in setupconfig-noSpot.json when setupApps.py is run with --no_spotwrap
PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
LAMDIR=${PREFIX}/lambda-python
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/lambda-python/mr
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
TS=1401861965497 #some early date
REG=us-west-2 #some early date
MAP=mapperNS
RED=reducerNS
RDC=reducerCoordinatorNS
DRI=driverNS
FNI=FnInvokerPyNS
STP=SpotTemplatePyNS
DBM=DBModPyNS
S3M=S3ModPyNS
SNS=SNSPyNS

cd ${LAMDIR}
. ./venv/bin/activate
cd ${CWDIR}
python downloadLogs.py "/aws/lambda/${MAP}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${RED}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${DRI}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${RDC}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${FNI}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${STP}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${DBM}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${S3M}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${SNS}" ${TS} -p ${PROF} --deleteOnly
deactivate

for i in `seq 1 10`;
do
    #delete the bucket contents for the job
    echo "s3 bucket cleanup"
    aws s3 rm s3://${MRBKT}/ --recursive --profile ${PROF}

    cd ${MRDIR}
    . ../venv/bin/activate
    #run the driver
    echo "MR app invocation..."
    aws lambda invoke --invocation-type Event --function-name ${DRI} --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"prefix\":\"pavlo/text/1node/uservisits/\",\"job_id\":\"${JOBID}\",\"mapper\":\"${MAP}\",\"reducer\":\"${RED}\",\"bucket\":\"big-data-benchmark\",\"jobBucket\":\"${MRBKT}\",\"region\":\"${REG}\",\"full_async\":\"yes\"}" outputfile

    #run the website app functions
    echo "Web app invocation..."
    aws lambda invoke --invocation-type Event --function-name ${FNI} --region ${REG} --profile cjk1 --payload "{\"eventSource\":\"ext:invokeCLI\",\"functionName\":\"arn:aws:lambda:${REG}:${ACCT}:function:${DBM}\",\"tablename\":\"triggerTable\",\"count\":\"10\"}" outputfile

  aws lambda invoke --invocation-type Event --function-name ${SNS} --region ${REG} --profile cjk1 --payload "{\"eventSource\":\"ext:invokeCLI\",\"topic\":\"arn:aws:sns:${REG}:${ACCT}:testtopic\",\"subject\":\"zoego${i}\",\"msg\":\"walk${RANDOM}\"}" outputfile

    aws lambda invoke --invocation-type Event --function-name ${S3M} --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"bkt\":\"cjklambdatrigger\",\"prefix\":\"PythonLambda\",\"fname\":\"todo${RANDOM}.txt\",\"file_content\":\"get dog food\"}" outputfile

    /bin/sleep 900 #seconds, so 15mins

    #download cloudwatch logs (and delete them)
    cd ${CWDIR}
    mkdir -p $i/APP/NS
    python downloadLogs.py "/aws/lambda/${MAP}" ${TS} -p ${PROF} --delete  > $i/APP/NS/map.log
    python downloadLogs.py "/aws/lambda/${RED}" ${TS} -p ${PROF} --delete > $i/APP/NS/red.log
    python downloadLogs.py "/aws/lambda/${DRI}" ${TS} -p ${PROF} --delete  > $i/APP/NS/driv.log
    python downloadLogs.py "/aws/lambda/${RDC}" ${TS} -p ${PROF} --delete > $i/APP/NS/coord.log
    python downloadLogs.py "/aws/lambda/${FNI}" ${TS} -p ${PROF} --delete > $i/APP/NS/fninv.log
    python downloadLogs.py "/aws/lambda/${SPT}" ${TS} -p ${PROF} --delete > $i/APP/NS/spottemp.log
    python downloadLogs.py "/aws/lambda/${DBM}" ${TS} -p ${PROF} --delete > $i/APP/NS/dbmod.log
    python downloadLogs.py "/aws/lambda/${S3M}" ${TS} -p ${PROF} --delete > $i/APP/NS/s3mod.log
    python downloadLogs.py "/aws/lambda/${SNS}" ${TS} -p ${PROF} --delete > $i/APP/NS/sns.log

    deactivate
    
done

