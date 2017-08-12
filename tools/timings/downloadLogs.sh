#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset args. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset args. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
MRBKT=spot-mr-bkt #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run without --no_spotwrap
MRBKTNS=spot-mr-bkt-ns #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
LAMDIR=${PREFIX}/lambda-python
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/lambda-python/mr
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
TS=1401861965497 #some early date

#download cloudwatch logs 
cd ${LAMDIR}
. ./venv/bin/activate
cd ${CWDIR}
i=$2
mkdir -p $i
echo mapper
python downloadLogs.py "/aws/lambda/mapper" ${TS} -p ${PROF} > $i/map.log
echo reducer
python downloadLogs.py "/aws/lambda/reducer" ${TS} -p ${PROF} > $i/red.log
echo driver
python downloadLogs.py "/aws/lambda/driver" ${TS} -p ${PROF} > $i/driv.log
echo reducerCoordinator
python downloadLogs.py "/aws/lambda/reducerCoordinator" ${TS} -p ${PROF} > $i/coord.log
echo sns
python downloadLogs.py "/aws/lambda/SNSPy" ${TS} -p ${PROF}  > $i/sns.log
echo s3
python downloadLogs.py "/aws/lambda/S3ModPy" ${TS} -p ${PROF} > $i/s3.log
echo db
python downloadLogs.py "/aws/lambda/DBModPy" ${TS} -p ${PROF}   > $i/db.log
echo fn
python downloadLogs.py "/aws/lambda/FnInvokerPy" ${TS} -p ${PROF}  > $i/fn.log
echo spot
python downloadLogs.py "/aws/lambda/SpotTemplatePy" ${TS} -p ${PROF} > $i/spot.log
deactivate
    
