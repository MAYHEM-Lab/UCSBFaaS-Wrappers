#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset AWS Account ID. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
ACCT=$2
MRBKT=spot-mr-bkt #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run
JOBID=job4000 #must match reducerCoordinator "job_id" in setupconfig.json when setupApps.py is run
PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
LAMDIR=${PREFIX}/lambda-python
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/lambda-python/mr
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
TS=1401861965497 #some early date
REG=us-west-2 
MAP=mapper
RED=reducer
RDC=reducerCoordinator
DRI=driver
FNI=FnInvokerPy
STP=SpotTemplatePy
DBM=DBModPy
S3M=S3ModPy
SNS=SNSPy

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
    mkdir -p $i/APP
    python downloadLogs.py "/aws/lambda/${MAP}" ${TS} -p ${PROF} --delete  > $i/APP/map.log
    python downloadLogs.py "/aws/lambda/${RED}" ${TS} -p ${PROF} --delete > $i/APP/red.log
    python downloadLogs.py "/aws/lambda/${DRI}" ${TS} -p ${PROF} --delete  > $i/APP/driv.log
    python downloadLogs.py "/aws/lambda/${RDC}" ${TS} -p ${PROF} --delete > $i/APP/coord.log
    python downloadLogs.py "/aws/lambda/${FNI}" ${TS} -p ${PROF} --delete > $i/APP/fninv.log
    python downloadLogs.py "/aws/lambda/${SPT}" ${TS} -p ${PROF} --delete > $i/APP/spottemp.log
    python downloadLogs.py "/aws/lambda/${DBM}" ${TS} -p ${PROF} --delete > $i/APP/dbmod.log
    python downloadLogs.py "/aws/lambda/${S3M}" ${TS} -p ${PROF} --delete > $i/APP/s3mod.log
    python downloadLogs.py "/aws/lambda/${SNS}" ${TS} -p ${PROF} --delete > $i/APP/sns.log

    deactivate
    
done

