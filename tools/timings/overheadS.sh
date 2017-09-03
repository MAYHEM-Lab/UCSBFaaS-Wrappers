#! /bin/bash
#TEST: S (static gammaray, original spotwrap)
if [ -z ${1+x} ]; then echo 'USAGE: ./overhead.sh aws_profile num_runs'; exit 1; fi
if [ -z ${2+x} ]; then echo 'USAGE: ./overhead.sh aws_profile num_runs'; exit 1; fi
PROF=$1
COUNT=$2
MRBKT=spot-mr-bkt #must match reducerCoordinator "permission" in config in setupApps.py
JOBID=job8000  #must match reducerCoordinator "job_id" in config in setupApps.py 

#update the below (must match lambda function names in configWestS.json
MAP="/aws/lambda/mapperS"
MAP_NAME=mapperS
RED_NAME=reducerS
RED="/aws/lambda/reducerS"
DRI="/aws/lambda/driverS"
RC="/aws/lambda/reducerCoordinatorS"
SPOTTABLE=spotFns #must match tablename (--spotFnsTableName) used in call to setupApps.py

PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
GRDIR=${PREFIX}/gammaRay
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${GRDIR}/apps/map-reduce
TS=1401861965497 #some early date

#setup environment
cd ${GRDIR}
. ./venv/bin/activate

#delete db entries
cd ${DYNDBDIR}
python dynamodelete.py -p ${PROF} ${SPOTTABLE}

#delete the logs
cd ${CWDIR}
python downloadLogs.py ${MAP} ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py ${RED} ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py ${DRI} ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py ${RC} ${TS} -p ${PROF} --deleteOnly

#do the same for no spotwrap
for i in `seq 1 ${COUNT}`;
do
    #delete the bucket contents for the job
    aws s3 rm s3://${MRBKT}/${JOBID} --recursive --profile ${PROF}

    cd ${MRDIR}
    rm -f overhead.out
    . ../venv/bin/activate
    #run the driver
    /usr/bin/time python driver.py ${MRBKT} ${JOBID} ${MAP_NAME} ${RED_NAME} --wait4reducers >> overhead.out
    mkdir -p ${i}
    rm ${i}/overhead.log
    mv overhead.out ${i}

    #download cloudwatch logs (and delete them)
    cd ${CWDIR}
    mkdir -p ${i}
    rm ${i}/*.log
    python downloadLogs.py ${MAP} ${TS} -p ${PROF} --delete  > ${i}/map.log
    python downloadLogs.py ${RED} ${TS} -p ${PROF} --delete  > ${i}/red.log
    python downloadLogs.py ${DRI} ${TS} -p ${PROF} --delete  > ${i}/driv.log
    python downloadLogs.py ${RC} ${TS} -p ${PROF} --delete  > ${i}/coord.log
    
done
deactivate
