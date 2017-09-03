#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset args. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
MRBKT=spot-mr-bkt #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run without --no_spotwrap
MRBKTNS=spot-mr-bkt-ns #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
JOBID=job4000  #must match reducerCoordinator "job_id" in setupconfig.json when setupApps.py is run without --no_spotwrap
JOBIDNS=job7000 #must match reducerCoordinator "job_id" in setupconfig.json when setupApps.py is run with --no_spotwrap
PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
LAMDIR=${PREFIX}/lambda-python
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/lambda-python/mr
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
TS=1401861965497 #some early date

#delete db entries
cd ${DYNDBDIR}
. ./venv/bin/activate
python dynamodelete.py -p ${PROF} ${SPOTTABLE}
deactivate
#delete the logs
cd ${LAMDIR}
. ./venv/bin/activate
cd ${CWDIR}
python downloadLogs.py "/aws/lambda/mapperNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/driverNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinatorNS" ${TS} -p ${PROF} --deleteOnly
deactivate

#do the same for no spotwrap
for i in `seq 1 10`;
do
    #delete the bucket contents for the job
    aws s3 rm s3://${MRBKTNS}/${JOBIDNS} --recursive --profile ${PROF}

    cd ${MRDIR}
    rm -f overhead.out
    . ../venv/bin/activate
    #run the driver
    /usr/bin/time python driver.py ${MRBKTNS} ${JOBIDNS} mapperNS reducerNS --wait4reducers >> overhead.out
    mkdir -p $i/NS
    mv overhead.out $i/NS

    #download cloudwatch logs (and delete them)
    cd ${CWDIR}
    mkdir -p $i/NS
    python downloadLogs.py "/aws/lambda/mapperNS" ${TS} -p ${PROF} --delete  > $i/NS/map.log
    python downloadLogs.py "/aws/lambda/reducerNS" ${TS} -p ${PROF} --delete  > $i/NS/red.log
    python downloadLogs.py "/aws/lambda/driverNS" ${TS} -p ${PROF} --delete  > $i/NS/driv.log
    python downloadLogs.py "/aws/lambda/reducerCoordinatorNS" ${TS} -p ${PROF} --delete  > $i/NS/coord.log
    deactivate
    
done
