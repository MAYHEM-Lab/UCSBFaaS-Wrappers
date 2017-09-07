#! /bin/bash
#TEST: S (static gammaray, original spotwrap)
if [ -z ${1+x} ]; then echo 'USAGE: ./overhead.sh aws_profile num_runs data_bucket_name prefix'; exit 1; fi
if [ -z ${2+x} ]; then echo 'USAGE: ./overhead.sh aws_profile num_runs data_bucket_name prefix'; exit 1; fi
if [ -z ${3+x} ]; then echo 'USAGE: ./overhead.sh aws_profile num_runs data_bucket_name prefix'; exit 1; fi
if [ -z ${4+x} ]; then echo 'Unset prefix as arg4 (full path to/including UCSBFaaS-Wrappers). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${5+x} ]; then echo 'Unset map-reduce-job-bucket as arg5. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
COUNT=$2
DATABKT=$3
PREFIX=$4
MRBKT=$5 #must match reducerCoordinator "permission" in config in setupApps.py
JOBID=$6  #must match reducerCoordinator "job_id" in config in setupApps.py 

#update the below (must match lambda function names in configWestC.json
MAP="/aws/lambda/mapperC"
MAP_NAME=mapperC
RED_NAME=reducerC
RED="/aws/lambda/reducerC"
DRI="/aws/lambda/driverC"
RC="/aws/lambda/reducerCoordinatorC"

GRDIR=${PREFIX}/gammaRay
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${GRDIR}/apps/map-reduce
TS=1401861965497 #some early date

#setup environment
cd ${GRDIR}
. ./venv/bin/activate

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
    mkdir -p ${i}/C
    rm -f ${i}/C/overhead.out
    mv overhead.out ${i}/C/

    #download cloudwatch logs (and delete them)
    cd ${CWDIR}
    mkdir -p ${i}/C
    rm -f ${i}/C/*.log
    python downloadLogs.py ${MAP} ${TS} -p ${PROF} --delete  > ${i}/C/map.log
    python downloadLogs.py ${RED} ${TS} -p ${PROF} --delete  > ${i}/C/red.log
    python downloadLogs.py ${DRI} ${TS} -p ${PROF} --delete  > ${i}/C/driv.log
    python downloadLogs.py ${RC} ${TS} -p ${PROF} --delete  > ${i}/C/coord.log
    
done
deactivate
