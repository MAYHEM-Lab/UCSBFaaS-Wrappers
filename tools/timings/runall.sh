#! /bin/bash
if [ -z ${1+x} ]; then echo 'USAGE: ./runall.sh aws_profile num_runs'; exit 1; fi
if [ -z ${2+x} ]; then echo 'USAGE: ./runall.sh aws_profile num_runs'; exit 1; fi

#this assume that everything has been cleaned out but that the apps have been deployed to lambda
export PREFIX=/Users/ckrintz/RESEARCH/lambda/
export ACCT=443592014519
export ROLE=adminlambda
export AWSRole=arn:aws:iam::${ACCT}:role/${ROLE}
export AWSPROFILE=cjk1

export SPOTBKTWEST=cjktestbkt
export SPOTBKTEAST=cjktestbkteast
export BDBENCH=cjk-gammaray-bdbenchmark
export APITESTBKT=cjk-apitest-bucket
export APITESTTABLE=cjk-apitest-bucket
export APIOUTBKT=cjk-spotwraptest0831
export SPOTTABLE=spotFns
export GAMMATABLE=gammaRays

export COUNT=50

cd ${PREFIX}/tools/timings
nohup ./overheadC.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} &
nohup ./overheadF.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} &
nohup ./overheadT.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} &
nohup ./overheadS.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} &
nohup ./overheadD.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} &
./micro.sh ${AWSPROFILE} 100
