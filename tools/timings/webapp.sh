#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset AWS Account ID. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${3+x} ]; then echo 'Unset prefix as arg3 (full path to/including UCSBFaaS-Wrappers). Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
ACCT=$2
PREFIX=$3
LAMDIR=${PREFIX}/lambda-python
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/lambda-python/mr
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
TS=1401861965497 #some early date
REG=us-west-2 #some early date
FNI=FnInvokerPyNS
STP=SpotTemplatePyNS
DBM=DBModPyNS
S3M=S3ModPyNS
SNS=SNSPyNS

cd ${LAMDIR}
. ./venv/bin/activate
cd ${CWDIR}
python downloadLogs.py "/aws/lambda/${FNI}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${STP}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${DBM}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${S3M}" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/${SNS}" ${TS} -p ${PROF} --deleteOnly
deactivate

for i in `seq 1 1`;
do

    #run the website app functions
    echo "Web app invocation..."
    aws lambda invoke --invocation-type Event --function-name ${FNI} --region ${REG} --profile cjk1 --payload "{\"eventSource\":\"ext:invokeCLI\",\"functionName\":\"arn:aws:lambda:${REG}:${ACCT}:function:${DBM}\",\"tablename\":\"triggerTable\",\"count\":\"10\"}" outputfile

  aws lambda invoke --invocation-type Event --function-name ${SNS} --region ${REG} --profile cjk1 --payload "{\"eventSource\":\"ext:invokeCLI\",\"topic\":\"arn:aws:sns:${REG}:${ACCT}:testtopic\",\"subject\":\"zoegoNS${i}\",\"msg\":\"walk${RANDOM}\"}" outputfile

    aws lambda invoke --invocation-type Event --function-name ${S3M} --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"bkt\":\"cjklambdatrigger\",\"prefix\":\"PythonLambda\",\"fname\":\"todo${RANDOM}.txt\",\"file_content\":\"get dog food\"}" outputfile

    /bin/sleep 30 #seconds, so 15mins

    #download cloudwatch logs (and delete them)
    cd ${CWDIR}
    mkdir -p cjk/$i/APP/NS
    python downloadLogs.py "/aws/lambda/${FNI}" ${TS} -p ${PROF} --delete > cjk/$i/APP/NS/fninv.log
    python downloadLogs.py "/aws/lambda/${SPT}" ${TS} -p ${PROF} --delete > cjk/$i/APP/NS/spottemp.log
    python downloadLogs.py "/aws/lambda/${DBM}" ${TS} -p ${PROF} --delete > cjk/$i/APP/NS/dbmod.log
    python downloadLogs.py "/aws/lambda/${S3M}" ${TS} -p ${PROF} --delete > cjk/$i/APP/NS/s3mod.log
    python downloadLogs.py "/aws/lambda/${SNS}" ${TS} -p ${PROF} --delete > cjk/$i/APP/NS/sns.log

    deactivate
    
done

