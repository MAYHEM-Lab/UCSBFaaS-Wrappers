#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset count (second var). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${3+x} ]; then echo 'Unset prefix as arg3 (full path to/including UCSBFaaS-Wrappers). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${4+x} ]; then echo 'Unset region as arg4. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${5+x} ]; then echo 'Unset accountID as arg5. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${6+x} ]; then echo 'Unset trigger bucket as arg6. (the prefix must be set to "pref[C,D,S,T,F]). Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
COUNT=$2
PREFIX=$3
REG=$4
ACCT=$5
TRIGGERBKT=$6
GRDIR=${PREFIX}/gammaRay
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
TS=1401861965497 #some early date

#SUFFIXES=( C S D F T B )
SUFFIXES=( C )
cd ${GRDIR}
. ./venv/bin/activate
cd ${CWDIR}

#see RUN_README for env. variable settings
#webapp.sh:SNSPy (topic_) -> triggers S3ModPy_ passes in bkt:${TRIGGERBKT}, fname:xxx, prefix:xxx in msg
        #S3Mod writes ${TRIGGERBKT} -> triggers FnInvoker, invokes DBMod ->
        #DBMod reads testTable and writes triggerTable (see FnInvoker.py for invoke call with params),
        #write to triggerTable -> triggers FnInvoker (does not invoke DBMod)

for suf in "${SUFFIXES[@]}"
do
    TOPIC="arn:aws:sns:${REG}:${ACCT}:topic${suf}"
    BKTPREFIX="pref${suf}"
    LLIST=( "SNSPy${suf}" "FnInvokerPy${suf}" "DBModPy${suf}" "S3ModPy${suf}" )
    for lambda in "${LLIST[@]}"
    do
        #cleanup
        python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} --deleteOnly
    done

    for i in `seq 1 ${COUNT}`;
    do
        aws lambda invoke --invocation-type Event --function-name SNSPy${suf} --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"ext:invokeCLI\",\"topic\":\"${TOPIC}\",\"subject\":\"sub1\",\"msg\":\"fname:testfile.txt:prefix:${BKTPREFIX}:bkt:${TRIGGERBKT}:xxx\"}" outputfile

        /bin/sleep 15 #seconds
        mkdir -p ${i}/APP/WEBAPP
        rm -f ${i}/APP/WEBAPP/*.log
        for lambda in "${LLIST[@]}"
        do
            #python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} --delete > $i/APP/WEBAPP/${lambda}.log
            python downloadLogs.py "/aws/lambda/${lambda}" ${TS} -p ${PROF} > $i/APP/WEBAPP/${lambda}.log
        done
    done
done
deactivate
