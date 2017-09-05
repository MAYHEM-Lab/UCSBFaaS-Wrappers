#! /bin/bash
#this program deletes all lambdas listed the config files under gammaRay/config/*.json and in restConfigsWest.json and restConfigsEast.json in the local dir, if present

#usage: ./cleanupLambda aws_profile arn:aws:iam::ACCT:role/LAMDAROLE
if [ -z ${1+x} ]; then echo 'Unset aws_profile (arg1). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset aws_role (second arg). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${3+x} ]; then echo 'Unset prefix as arg3 (full path to/including UCSBFaaS-Wrappers). Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
export AWSRole=$2
PREFIX=$3
GRMDIR=${PREFIX}/gammaRay
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/lambda-python/mr

cd ${GRMDIR}
. venv/bin/activate

for i in `ls configs/*.json`; 
do
    python setupApps.py -p ${PROF} --deleteAll -f $i
done
if [ -e ${TOOLSDIR}/restConfigsWest.json ]
then
python setupApps.py -p ${PROF} --deleteAll -f ${TOOLSDIR}/restConfigsWest.json
fi
if [ -e ${TOOLSDIR}/restConfigsEast.json ]
then
python setupApps.py -p ${PROF} --deleteAll -f ${TOOLSDIR}/restConfigsEast.json
fi

deactivate
