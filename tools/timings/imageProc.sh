#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset count (second var). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${3+x} ]; then echo 'Unset prefix as arg3 (full path to/including UCSBFaaS-Wrappers). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${4+x} ]; then echo 'Unset region where starting lambda (ImageProcPy*) is as arg4. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${5+x} ]; then echo 'Unset region where cross-region lambda (UpdateWeb*) is as arg5. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
COUNT=$2
PREFIX=$3
REG=$4
ACCT=$5
GRDIR=${PREFIX}/gammaRay
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
TS=1401861965497 #some early date

SUFFIXES=( C S D F T B )
cd ${GRDIR}
. ./venv/bin/activate
cd ${CWDIR}

for suf in "${SUFFIXES[@]}"
do
    TOPIC="arn:aws:sns:${REG}:${ACCT}:topic${suf}"
    BKTPREFIX="pref${suf}"
    LLIST=( "ImageProcPy${suf}" "DBSyncPy${suf}" "UpdateWebsite${suf}" )
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

    for i in `seq 1 ${COUNT}`;
    do
        aws lambda invoke --invocation-type Event --function-name ImageProcPy${suf} --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"name\":\"cjktestbkt\",\"key\":\"imgProc/d1.jpg\"}" outputfile

        /bin/sleep 30 #seconds
        mkdir -p ${i}/APP/IMGPROC
        rm -f ${i}/APP/IMGPROC/*.log
        for lambda in "${LLIST[@]}"
        do
        if [[ ${lambda} == UpdateWeb* ]] ;
        then
            python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} --region us-east-1 > $i/APP/IMGPROC/${lambda}.log
        else
            python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} > $i/APP/IMGPROC/${lambda}.log
        fi
        done
    done
done
deactivate
