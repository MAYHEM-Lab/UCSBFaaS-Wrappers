#! /bin/bash
#this assume that everything has been cleaned out but that the apps have been deployed to lambda
export PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
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

export COUNT=1
cd ${PREFIX}/tools/timings
echo; echo overheadC
nohup ./overheadC.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} 

echo; echo overheadF
nohup ./overheadF.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} 

echo; echo overheadT
nohup ./overheadT.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} 

echo; echo overheadS
nohup ./overheadS.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} 
python ../get_stream_data.py arn:aws:dynamodb:us-west-2:443592014519:table/spotFns/stream/2017-09-03T22:09:22.445 -p ${AWSPROFILE} >& streamMRS.out

echo; echo overheadD
nohup ./overheadD.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} 
python ../get_stream_data.py arn:aws:dynamodb:us-west-2:443592014519:table/gammaRays/stream/2017-09-01T21:10:57.071 -p ${AWSPROFILE} >&  streamMRD.out

#echo; echo micro
#./micro.sh ${AWSPROFILE} 100
#python ../get_stream_data.py arn:aws:dynamodb:us-west-2:443592014519:table/spotFns/stream/2017-09-03T22:09:22.445 -p ${AWSPROFILE} >& streamMicroS.out
#python ../get_stream_data.py arn:aws:dynamodb:us-west-2:443592014519:table/gammaRays/stream/2017-09-01T21:10:57.071 -p ${AWSPROFILE} >&  streamMicroD.out
