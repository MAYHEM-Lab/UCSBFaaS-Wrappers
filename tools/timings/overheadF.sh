#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset args. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
MRBKT=spot-mr-bkt-f #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run without --no_spotwrap
JOBID=job6000  #must match reducerCoordinator "job_id" in setupconfig.json when setupApps.py is run without --no_spotwrap
PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
LAMDIR=${PREFIX}/lambda-python
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/gammaRay/apps/map-reduce
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
GAMMATABLE=gammaRays #must match tablename used by SpotWrap.py.template
TS=1401861965497 #some early date

#delete db entries
cd ${LAMDIR}
. ./venv/bin/activate
cd ${DYNDBDIR}
python dynamodelete.py -p ${PROF} ${SPOTTABLE}
python dynamodelete.py -p ${PROF} ${GAMMATABLE}
#delete the logs
cd ${CWDIR}
python downloadLogs.py "/aws/lambda/mapperF" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerF" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/driverF" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinatorF" ${TS} -p ${PROF} --deleteOnly
deactivate

#do the same for no spotwrap
for i in `seq 1 10`;
do
    #delete the bucket contents for the job
    aws s3 rm s3://${MRBKT}/${JOBID} --recursive --profile ${PROF}

    cd ${MRDIR}
    rm -f overhead.out
    . ../venv/bin/activate
    #run the driver
    /usr/bin/time python driver.py ${MRBKT} ${JOBID} mapperF reducerF --wait4reducers >> overhead.out
    mkdir -p $i/F
    mv overhead.out $i/F

    #download cloudwatch logs (and delete them)
    cd ${CWDIR}
    mkdir -p $i/F
    python downloadLogs.py "/aws/lambda/mapperF" ${TS} -p ${PROF} --delete  > $i/F/map.log
    python downloadLogs.py "/aws/lambda/reducerF" ${TS} -p ${PROF} --delete  > $i/F/red.log
    python downloadLogs.py "/aws/lambda/driverF" ${TS} -p ${PROF} --delete  > $i/F/driv.log
    python downloadLogs.py "/aws/lambda/reducerCoordinatorF" ${TS} -p ${PROF} --delete  > $i/F/coord.log
    deactivate
    
done
