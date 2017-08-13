#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset AWS Account ID. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
ACCT=$2
MRBKT=spot-mr-bkt #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run without --no_spotwrap
MRBKTNS=spot-mr-bkt-ns #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
JOBID=job4000  #must match reducerCoordinator "job_id" in setupconfig.json when setupApps.py is run without --no_spotwrap
JOBIDNS=jobNS4000 #must match reducerCoordinator "job_id" in setupconfig.json when setupApps.py is run with --no_spotwrap
PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
LAMDIR=${PREFIX}/lambda-python
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/lambda-python/mr
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
TS=1401861965497 #some early date
REG=us-west-2 #some early date

#delete db entries
cd ${DYNDBDIR}
. ./venv/bin/activate
python dynamodelete.py -p ${PROF} ${SPOTTABLE}
deactivate
#delete the logs
cd ${LAMDIR}
. ./venv/bin/activate
cd ${CWDIR}
python downloadLogs.py "/aws/lambda/mapper" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducer" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/driver" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinator" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/FnInvokerPy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/SpotTemplatePy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/DBModPy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/S3ModPy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/SNSPy" ${TS} -p ${PROF} --deleteOnly
deactivate

for i in `seq 1 1`;
do
    #delete the bucket contents for the job
    echo "s3 bucket cleanup"
    aws s3 rm s3://${MRBKT}/ --recursive --profile ${PROF}

    cd ${MRDIR}
    . ../venv/bin/activate
    #run the driver
    echo "MR app invocation..."
    aws lambda invoke --invocation-type Event --function-name driver --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"prefix\":\"pavlo/text/1node/uservisits/\",\"job_id\":\"${JOBID}\",\"mapper\":\"mapper\",\"reducer\":\"reducer\",\"bucket\":\"big-data-benchmark\",\"jobBucket\":\"${MRBKT}\",\"region\":\"${REG}\",\"full_async\":\"yes\"}" outputfile

    #run the website app functions
    echo "Web app invocation..."
    aws lambda invoke --invocation-type Event --function-name SNSPy --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"topic\":\"arn:aws:sns:us-west-2:${ACCT}:testtopic\",\"subject\":\"zoego\",\"msg\":\"${i}\"}" outputfile

    aws lambda invoke --invocation-type Event --function-name S3ModPy --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"bkt\":\"cjklambdatrigger\",\"prefix\":\"PythonLambda\",\"fname\":\"todo${i}.txt\",\"file_content\":\"get dog food\"}" outputfile

    aws lambda invoke --invocation-type Event --function-name DBModPy --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"tablename\":\"testTable\",\"mykey\":\"cjkDBModPy${i}\",\"myval\":\"${RANDOM}\"}" outputfile

    aws lambda invoke --invocation-type Event --function-name DBModPy --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"tablename\":\"triggerTable\",\"mykey\":\"cjkDBModPy${i}\",\"myval\":\"${RANDOM}\"}" outputfile

    aws lambda invoke --invocation-type Event --function-name FnInvokerPy --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"functionName\":\"arn:aws:lambda:us-west-2:${ACCT}:function:DBModPy\",\"tablename\":\"triggerTable\",\"mykey\":\"cjkFInfPy${RANDOM}\",\"myval\":\"${RANDOM}\"}" outputfile

    aws lambda invoke --invocation-type Event --function-name FnInvokerPy --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"functionName\":\"arn:aws:lambda:us-west-2:${ACCT}:function:SpotTemplatePy\"}" outputfile

    aws lambda invoke --invocation-type Event --function-name SpotTemplatePy --region us-west-2 --profile cjk1 --payload "{\"eventSource\":\"ext:invokeCLI\",\"functionName\":\"arn:aws:lambda:us-west-2:${ACCT}:function:DBModPy\",\"tablename\":\"testTable\",\"mykey\":\"cjkSTPy${RANDOM}\",\"myval\":\"${RANDOM}\"}" outputfile
    /bin/sleep 900 #seconds, so 15mins

    #download cloudwatch logs (and delete them)
    cd ${CWDIR}
    mkdir -p $i/MR
    python downloadLogs.py "/aws/lambda/mapper" ${TS} -p ${PROF}  > $i/MR/map.log
    python downloadLogs.py "/aws/lambda/reducer" ${TS} -p ${PROF} > $i/MR/red.log
    python downloadLogs.py "/aws/lambda/driver" ${TS} -p ${PROF}  > $i/MR/driv.log
    python downloadLogs.py "/aws/lambda/reducerCoordinator" ${TS} -p ${PROF} > $i/MR/coord.log
    python downloadLogs.py "/aws/lambda/FnInvokerPy" ${TS} -p ${PROF} > $i/fninv.log
    python downloadLogs.py "/aws/lambda/SpotTemplatePy" ${TS} -p ${PROF} > $i/spottemp.log
    python downloadLogs.py "/aws/lambda/DBModPy" ${TS} -p ${PROF} > $i/dbmod.log
    python downloadLogs.py "/aws/lambda/S3ModPy" ${TS} -p ${PROF} > $i/s3mod.log
    python downloadLogs.py "/aws/lambda/SNSPy" ${TS} -p ${PROF} > $i/sns.log

    #comment the above and uncomment the below to delete the logs once downloaded
    #alternatively, you can use cleanupAWS.sh to delete all logs...

    #python downloadLogs.py "/aws/lambda/mapper" ${TS} -p ${PROF} --delete  > $i/MR/map.log
    #python downloadLogs.py "/aws/lambda/reducer" ${TS} -p ${PROF} --delete > $i/MR/red.log
    #python downloadLogs.py "/aws/lambda/driver" ${TS} -p ${PROF} --delete  > $i/MR/driv.log
    #python downloadLogs.py "/aws/lambda/reducerCoordinator" ${TS} -p ${PROF} --delete > $i/MR/coord.log
    #python downloadLogs.py "/aws/lambda/FnInvokerPy" ${TS} -p ${PROF} --delete > $i/fninv.log
    #python downloadLogs.py "/aws/lambda/SpotTemplatePy" ${TS} -p ${PROF} --delete > $i/spottemp.log
    #python downloadLogs.py "/aws/lambda/DBModPy" ${TS} -p ${PROF} --delete > $i/dbmod.log
    #python downloadLogs.py "/aws/lambda/S3ModPy" ${TS} -p ${PROF} --delete > $i/s3mod.log
    #python downloadLogs.py "/aws/lambda/SNSPy" ${TS} -p ${PROF} --delete > $i/sns.log

    deactivate
    
    #download the db and then delete its entries
    #cd ${DYNDBDIR}
    #. ./venv/bin/activate
    #rm -rf dump
    #python dynamodump.py -m backup -r ${REG} -p ${PROF} -s ${SPOTTABLE}
    #mkdir -p $i/MR
    #rm -rf $i/MR/*
    #mv dump $i/MR/
    #python dynamodelete.py -p ${PROF} ${SPOTTABLE}
    #deactivate
done

