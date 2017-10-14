#! /bin/bash
if [ "$#" -ne 11 ]; then
    echo "USAGE: ./overhead.sh aws_profile num_runs data_bucket_name prefix jobid C_job_bkt D_job_bkt F_job_bkt  S_job_bkt  T_job_bkt B_job_bkt"
    exit 1
fi
PROF=$1
COUNT=$2
DATABKT=$3
PREFIX=$4
JOBID=$5  #must match reducerCoordinator "job_id" in config in setupApps.py for triggerBuckets

MRBKTC=$6 #must match reducerCoordinator "permission" in config in setupApps.py for triggerBuckets
MRBKTD=$7 #must match reducerCoordinator "permission" in config in setupApps.py for triggerBuckets
MRBKTF=$8 #must match reducerCoordinator "permission" in config in setupApps.py for triggerBuckets
MRBKTS=$9 #must match reducerCoordinator "permission" in config in setupApps.py for triggerBuckets
MRBKTT=${10} #must match reducerCoordinator "permission" in config in setupApps.py for triggerBuckets
MRBKTB=${11} #must match reducerCoordinator "permission" in config in setupApps.py for triggerBuckets

#0-base indexed via "${BKTLIST[2]}" (is F)
#must be in same order as SUFFIXES!!
BKTLIST=( 
    ${MRBKTC} \
    ${MRBKTD} \
    ${MRBKTF} \
    ${MRBKTS} \
    ${MRBKTT} \
    ${MRBKTB} \
)
SUFFIXES=( C D F S T B )
#for testing or re-running, put the suffixes in here that you want to run
RUNTHESE=( B )

#update the below (must match lambda function names in configWestC.json
FMAP="/aws/lambda/mapper"
FMAP_NAME=mapper
FRED_NAME=reducer
FRED="/aws/lambda/reducer"
FRC="/aws/lambda/reducerCoordinator"

GRDIR=${PREFIX}/gammaRay
CWDIR=${PREFIX}/tools/cloudwatch
MRDIR=${GRDIR}/apps/map-reduce
TS=1401861965497 #some early date

#setup environment
cd ${GRDIR}
. ./venv/bin/activate

ITER=0
for suf in "${SUFFIXES[@]}"
do
    #we have to do this to ensure that SUFFIXES stays in sync with BKTLIST
    SKIP="donotrun"
    for torun in "${RUNTHESE[@]}"
    do
        if [ "${suf}" = "${torun}" ]; then
            SKIP="run"
            break
        fi
    done
    #echo ${BKTLIST[${ITER}]} ${FMAP}${suf} ${SKIP}

    #Run it if we included it in RUNTHESE
    if [ "${SKIP}" = "run" ]; then
        MRBKT=${BKTLIST[${ITER}]}
        MAP=${FMAP}${suf}
        MAP_NAME=${FMAP_NAME}${suf}
        RED=${FRED}${suf}
        RED_NAME=${FRED_NAME}${suf}
        RC=${FRC}${suf}
        echo "Running experiment:" ${MRBKT} ${MAP} ${MAP_NAME} ${RED} ${RED_NAME} ${RC} ${JOBID} ${DATABKT} ${COUNT} times
        for i in `seq 1 ${COUNT}`;
        do
            #clean out the s3 bucket we are about to use
            aws s3 rm s3://${MRBKT}/${JOBID} --recursive --profile ${PROF}
            #delete the logs
            cd ${CWDIR}
            python downloadLogs.py ${MAP} ${TS} -p ${PROF} --deleteOnly
            python downloadLogs.py ${RED} ${TS} -p ${PROF} --deleteOnly
            python downloadLogs.py ${RC} ${TS} -p ${PROF} --deleteOnly

            #run job
            cd ${MRDIR}
            rm -f overhead.out
            echo "Job: driver, " ${i} ${MRBKT} ${JOBID} ${MAP_NAME} ${RED_NAME} ${DATABKT} ${COUNT}
            #use the driver
            /usr/bin/time python driver.py ${MRBKT} ${JOBID} ${MAP_NAME} ${RED_NAME} --wait4reducers --databkt ${DATABKT} > overhead.out
            mkdir -p ${i}/MRSYNC/${suf}
            rm -f ${i}/MRSYNC/${suf}/overhead.out
            mv overhead.out ${i}/MRSYNC/${suf}/
    
            echo "sleeping 45secs..."
            /bin/sleep 45 #seconds to wait for RC logs to commit
        
            echo "downloading logs"
            #download cloudwatch logs (and delete them)
            cd ${CWDIR}
            mkdir -p ${i}/MRSYNC/${suf}
            rm -f ${i}/MRSYNC/${suf}/*.log
            echo ${MAP} ${TS} ${PROF} ${i}/MRSYNC/${suf}
            python downloadLogs.py ${MAP} ${TS} -p ${PROF} > ${i}/MRSYNC/${suf}/map.log
            python downloadLogs.py ${RED} ${TS} -p ${PROF} > ${i}/MRSYNC/${suf}/red.log
            python downloadLogs.py ${RC} ${TS} -p ${PROF} > ${i}/MRSYNC/${suf}/coord.log
            echo done downloading logs...
        
        done
    fi
    ((ITER++))  #used to keep SUFFIXES and BKTLIST in sync
done
deactivate
