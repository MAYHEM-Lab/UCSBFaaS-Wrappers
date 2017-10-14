#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset count (second var). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${3+x} ]; then echo 'Unset prefix as arg3 (full path to/including UCSBFaaS-Wrappers). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${4+x} ]; then echo 'Unset region as arg4. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${5+x} ]; then echo 'Unset accountID as arg5. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${6+x} ]; then echo 'Unset trigger bucket prefix (FNI_TRIGGERBKT) as arg6. This script will add the suffixes [C,D,S,T,F]). Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
COUNT=$2
PREFIX=$3
REG=$4
ACCT=$5
TRIGGERBKTPREFIX=$6
GRDIR=${PREFIX}/gammaRay
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
TS=1401861965497 #some early date

SUFFIXES=( C S D F T B )
SUFFIXES=(  B )
cd ${GRDIR}
. ./venv/bin/activate
cd ${CWDIR}

#see RUN_README for env. variable settings
#tools/timings/webapp.sh:SNSPy (topic_) ->
        #triggers S3ModPy_ passes in via the SNS message:
        #bkt:${FNI_TRIGGERBKT_}, fname:xxx, prefix:pref_ (_=[CBDSTF]) anywhere in message
        #S3Mod writes ${FNI_TRIGGERBKT_}
        #--> which triggers FnInvokerPy_ which invokes DBModPy_ ->
        #DBMod reads testTable and writes ${WEBAPP_DBMOD_TRIGGER_TABLE_PREFIX_}  for _=[CBDSTF]
        #(see FnInvoker.py for invoke call with params),
        #the write to ${WEBAPP_DBMOD_TRIGGER_TABLE_PREFIX_}->triggers FnInvokerPy (does not invoke DBModPy)

for suf in "${SUFFIXES[@]}"
do
    TOPIC="arn:aws:sns:${REG}:${ACCT}:topic${suf}"
    BKTPREFIX="pref${suf}"
    lowersuf="$(tr [A-Z] [a-z] <<< "$suf")"
    BKT="${TRIGGERBKTPREFIX}-${lowersuf}"
    LLIST=( "SNSPy${suf}" "FnInvokerPy${suf}" "DBModPy${suf}" "S3ModPy${suf}" )

    for i in `seq 1 ${COUNT}`;
    do
        for lambda in "${LLIST[@]}"
        do
            #cleanup
            python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} --deleteOnly
        done

        #runit
        aws lambda invoke --invocation-type Event --function-name SNSPy${suf} --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"topic\":\"${TOPIC}\",\"subject\":\"sub1\",\"msg\":\"fname:testfile.txt:prefix:${BKTPREFIX}:bkt:${BKT}:xxx\"}" outputfile

        /bin/sleep 30 #seconds
        mkdir -p ${i}/APP/WEBAPP/${suf}
        rm -f ${i}/APP/WEBAPP/${suf}/*.log
        for lambda in "${LLIST[@]}"
        do
            #python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} --delete > $i/APP/WEBAPP/${suf}/${lambda}.log
            python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} > $i/APP/WEBAPP/${suf}/${lambda}.log
        done
    done
done
deactivate
