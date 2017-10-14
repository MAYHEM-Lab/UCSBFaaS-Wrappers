#! /bin/bash
if [ "$#" -ne 12 ]; then
    echo "USAGE: ./mr.sh aws_profile num_runs data_bucket_name prefix jobid C_job_bkt D_job_bkt F_job_bkt  S_job_bkt  T_job_bkt B_job_bkt REGION"
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

REG=${12} 

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
RUNTHESE=( F B )
RUNTHESE=( B )

#update the below (must match lambda function names in configWestC.json
FMAP="/aws/lambda/mapper"
FMAP_NAME=mapper
FRED_NAME=reducer
FRED="/aws/lambda/reducer"
FRC="/aws/lambda/reducerCoordinator"
FDRI="/aws/lambda/driver"
FDRI_NAME="driver"

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
        DRI=${FDRI}${suf}
        DRI_NAME=${FDRI_NAME}${suf}
        echo "Running experiment:" ${MRBKT} ${MAP} ${MAP_NAME} ${RED} ${RED_NAME} ${RC} ${DRI} ${DRI_NAME} ${COUNT} times
        for i in `seq 1 ${COUNT}`;
        do
            #clean out the s3 bucket we are about to use
            aws s3 rm s3://${MRBKT}/${JOBID} --recursive --profile ${PROF}
            #delete the logs
            cd ${CWDIR}
            python downloadLogs.py ${MAP} ${TS} -p ${PROF} --deleteOnly
            python downloadLogs.py ${RED} ${TS} -p ${PROF} --deleteOnly
            python downloadLogs.py ${RC} ${TS} -p ${PROF} --deleteOnly
            python downloadLogs.py ${DRI} ${TS} -p ${PROF} --deleteOnly
            #run job
            cd ${MRDIR}
            #use the API
            echo "Invoking:" $DRI $REG $PROF $JOBID $MAP $RED $DATABKT $MRBKT 
            aws lambda invoke --invocation-type Event --function-name ${DRI_NAME} --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"prefix\":\"pavlo/text/1node/uservisits/\",\"job_id\":\"${JOBID}\",\"mapper\":\"${MAP_NAME}\",\"reducer\":\"${RED_NAME}\",\"bucket\":\"${DATABKT}\",\"jobBucket\":\"${MRBKT}\",\"region\":\"${REG}\",\"full_async\":\"yes\"}" outputfile
        
            /bin/sleep 600 #seconds, so 10mins for the job to finish (add more time if bucket is in another region...)
    
            #download cloudwatch logs (and delete them)
            cd ${CWDIR}
            mkdir -p ${i}/${suf}/MRASYNC
            echo ${MAP} ${TS} ${PROF} ${i}/${suf}
            python downloadLogs.py ${MAP} ${TS} -p ${PROF} > ${i}/${suf}/MRASYNC/map.log
            python downloadLogs.py ${RED} ${TS} -p ${PROF} > ${i}/${suf}/MRASYNC/red.log
            python downloadLogs.py ${RC} ${TS} -p ${PROF}  > ${i}/${suf}/MRASYNC/coord.log
            python downloadLogs.py ${DRI} ${TS} -p ${PROF} > ${i}/${suf}/MRASYNC/dri.log
            echo done downloading logs...
        
        done
    fi
    ((ITER++))  #used to keep SUFFIXES and BKTLIST in sync
done
