#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset count (second var). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${3+x} ]; then echo 'Unset prefix as arg3 (full path to/including UCSBFaaS-Wrappers). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${4+x} ]; then echo 'Unset region where starting lambda (ImageProcPy*) is as arg4. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${5+x} ]; then echo 'Unset region where cross-region lambda (UpdateWeb*) is as arg5. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${6+x} ]; then echo 'Unset bucket where /imgProc/d1.jpg (any picture will work here) is as arg6. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${7+x} ]; then echo 'Unset table prefix (IMG_DBSYNC_TRIGGER_TABLE_PREFIX). Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
COUNT=$2
PREFIX=$3
REG=$4
ACCT=$5
BKT=$6
TABLEPREF=$7
BKTKEY=imgProc/d1.jpg
GRDIR=${PREFIX}/gammaRay
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
TS=1401861965497 #some early date

SUFFIXES=( C S D F T B )
cd ${GRDIR}
. ./venv/bin/activate
cd ${CWDIR}

#see RUN_README for env. variable settings
#imageProc.sh: ImgProc_ -> CLI Invoked calls http, rekognition, ${IMAGEPROC_DBSYNC} DB table write
        #${IMAGEPROC_DBSYNC} write triggers DBSyncPy (all of them which is fine b/c we only download the _ log)
        #DBSyncPy writes ${EASTSYNCTABLE} in east region
        #UpdateWebsite (all of them) in east is triggered by ${EASTSYNCTABLE} write and
        #invokes http

for suf in "${SUFFIXES[@]}"
do
    LLIST=( "ImageProcPy${suf}" "DBSyncPy${suf}" "UpdateWebsite${suf}" )
    for i in `seq 1 ${COUNT}`;
    do
        for lambda in "${LLIST[@]}"
        do
            #cleanup
            if [[ ${lambda} == UpdateWeb* ]] ;
            then
                python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} --deleteOnly --region us-east-1
            else
                python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} --deleteOnly
            fi
        done

        #runit
        aws lambda invoke --invocation-type Event --function-name ImageProcPy${suf} --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"name\":\"${BKT}\",\"key\":\"${BKTKEY}\",\"tableName\":\"${TABLEPREF}${suf}\"}" outputfile

        /bin/sleep 45 #seconds
        mkdir -p ${i}/APP/IMGPROC/${suf}
        rm -f ${i}/APP/IMGPROC/${suf}/*.log
        for lambda in "${LLIST[@]}"
        do
            if [[ ${lambda} == UpdateWeb* ]] ;
            then
                python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} --region us-east-1 > ${i}/APP/IMGPROC/${suf}/${lambda}.log
            else
                python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} > ${i}/APP/IMGPROC/${suf}/${lambda}.log
            fi
        done
    done
done
deactivate
