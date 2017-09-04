#! /bin/bash
#TEST: S (static gammaray, original spotwrap)
if [ -z ${1+x} ]; then echo 'USAGE: ./overhead.sh aws_profile num_runs data_bucket_name'; exit 1; fi
if [ -z ${2+x} ]; then echo 'USAGE: ./overhead.sh aws_profile num_runs data_bucket_name'; exit 1; fi
if [ -z ${3+x} ]; then echo 'USAGE: ./overhead.sh aws_profile num_runs data_bucket_name'; exit 1; fi
#DATABKT=big-data-benchmark
DATABKT=$3
PROF=$1
COUNT=$2
MRBKT=spot-mr-bkt-gr #must match reducerCoordinator "permission" in config in setupApps.py
JOBID=job8000  #must match reducerCoordinator "job_id" in config in setupApps.py 
DATABKTPREFIX="pavlo/text/1node/uservisits/"

#update the below (must match lambda function names in configWestG.json
MAP="/aws/lambda/mapperD"
MAP_NAME=mapperD
RED_NAME=reducerD
RED="/aws/lambda/reducerD"
DRI="/aws/lambda/driverD"
RC="/aws/lambda/reducerCoordinatorD"
SPOTTABLE=gammaRays #must match tablename (--spotFnsTableName) used in call to setupApps.py

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
    #run the driver
    /usr/bin/time python driver.py ${MRBKT} ${JOBID} ${MAP_NAME} ${RED_NAME} --wait4reducers --databkt ${DATABKT} > overhead.out
    mkdir -p ${i}/D
    rm -f ${i}/D/overhead.out
    mv overhead.out ${i}/D/

    #download cloudwatch logs (and delete them)
    cd ${CWDIR}
    mkdir -p ${i}/D
    rm -f ${i}/D/*.log
    python downloadLogs.py ${MAP} ${TS} -p ${PROF} --delete  > ${i}/D/map.log
    python downloadLogs.py ${RED} ${TS} -p ${PROF} --delete  > ${i}/D/red.log
    python downloadLogs.py ${DRI} ${TS} -p ${PROF} --delete  > ${i}/D/driv.log
    python downloadLogs.py ${RC} ${TS} -p ${PROF} --delete  > ${i}/D/coord.log
    
done
deactivate
