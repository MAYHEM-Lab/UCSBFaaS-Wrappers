#! /bin/bash
#this assumes that everything has been cleaned out but that the apps have been deployed to lambda
export PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
export ACCT=443592014519
export ROLE=adminlambda
export AWSRole=arn:aws:iam::${ACCT}:role/${ROLE}
export AWSROLE=arn:aws:iam::${ACCT}:role/${ROLE}
export AWSPROFILE=cjk1
export REG=us-west-2
export XREG=us-east-1
export FLEECEDIR=${PREFIX}/fleece0.13.0
export FLEECE=${FLEECEDIR}/venv/lib/python3.6/site-packages/fleece
export BFLEECEDIR=${PREFIX}/fleece0.13.0lite
export BFLEECE=${BFLEECEDIR}/venv/lib/python3.6/site-packages/fleece
export BOTOCOREDIR=${PREFIX}/boto144
export BOTOCORE=${BOTOCOREDIR}/venv/lib/python3.6/site-packages/botocore
export LOCALLIBDIR=${PREFIX}/gammaRay
export LOCALLIBS=${LOCALLIBDIR}/venv/lib/python3.6/site-packages
export BDBENCH=cjk-gammaray-bdbenchmark
export SPOTTABLE=spotFns
export GAMMATABLE=gammaRays
export SPOTBKTWEST=cjktestbkt
export SPOTBKTEAST=cjktestbkteast
export APITESTBKT=cjk-apitest-bucket
export TRIGGERBKT=cjklambdatrigger
export EASTSYNCTABLE=eastSyncTable
export APITESTTABLE=noTriggerTestTable
export WEBAPPTRIGGERTABLE=triggerTable
export IMAGEPROC_DBSYNC=imageLabels
export GR_STREAMID=2017-09-09T20:03:35.795
export SPOT_STREAMID=2017-09-07T18:35:46.003
export MRBKTS=spot-mr-bkt
export MRBKTF=spot-mr-bkt-f
export MRBKTD=spot-mr-bkt-gr
export MRBKTC=spot-mr-bkt-ns
export MRBKTT=spot-mr-bkt-t
export MRBKTB=spot-mr-bkt-b
export JOBID=job8000
export MRDIR=${PREFIX}/gammaRay/apps/map-reduce
export CWDIR=${PREFIX}/tools/cloudwatch

######imageproc########
export COUNT=2
cd ${PREFIX}/tools/timings
echo; echo imageproc
./imageProc.sh ${AWSPROFILE} ${COUNT} ${PREFIX} ${REG} ${XREG} ${SPOTBKTWEST}
cd ${LOCALLIBDIR}  #this should be gammaRays directory for most 
source venv/bin/activate
cd ${PREFIX}/tools  #download the stream data and append it to stream base (save both)
python get_stream_data.py arn:aws:dynamodb:${REG}:${ACCT}:table/${SPOTTABLE}/stream/${SPOT_STREAMID} -p ${AWSPROFILE} >& streamS.new
diff -b -B streamS.base streamS.new| awk -F"> " '{print $2}' > imageProcS.stream
cat imageProcS.stream >> streamS.base
python get_stream_data.py arn:aws:dynamodb:${REG}:${ACCT}:table/${GAMMATABLE}/stream/${GR_STREAMID} -p ${AWSPROFILE} >&  streamD.new
diff -b -B streamD.base streamD.new| awk -F"> " '{print $2}' > imageProcD.stream
cat imageProcD.stream >> streamD.base
deactivate
./cleanupDB.sh ${AWSPROFILE} ${PREFIX}
/bin/sleep 30 #seconds

########webapp############
#webapp
export COUNT=2
cd ${PREFIX}/tools/timings
deactivate
./webapp.sh ${AWSPROFILE} ${COUNT} ${PREFIX} ${REG} ${ACCT} ${TRIGGERBKT}
cd ${LOCALLIBDIR}  #this should be gammaRays directory for most 
source venv/bin/activate
cd ${PREFIX}/tools  #download the stream data and append it to stream base (save both)
python get_stream_data.py arn:aws:dynamodb:${REG}:${ACCT}:table/${SPOTTABLE}/stream/${SPOT_STREAMID} -p ${AWSPROFILE} >& streamS.new
diff -b -B streamS.base streamS.new| awk -F"> " '{print $2}' > webappS.stream
cat webappS.stream >> streamS.base
python get_stream_data.py arn:aws:dynamodb:${REG}:${ACCT}:table/${GAMMATABLE}/stream/${GR_STREAMID} -p ${AWSPROFILE} >&  streamD.new
diff -b -B streamD.base streamD.new| awk -F"> " '{print $2}' > webappD.stream
cat webappD.stream >> streamD.base
deactivate
./cleanupDB.sh ${AWSPROFILE} ${PREFIX}
/bin/sleep 30 #seconds

######overheadMR########
#export COUNT=1
#cd ${PREFIX}/tools/timings
#echo; echo overheadMR
#./mr.sh ${AWSPROFILE} ${COUNT} ${BDBENCH} ${PREFIX} ${JOBID} ${MRBKTC} ${MRBKTD} ${MRBKTF} ${MRBKTS} ${MRBKTT} ${MRBKTB} ${REG}
#cd ${LOCALLIBDIR}  #this should be gammaRays directory for most 
#source venv/bin/activate
#cd ${PREFIX}/tools  #download the stream data and append it to stream base (save both)
#python get_stream_data.py arn:aws:dynamodb:${REG}:${ACCT}:table/${SPOTTABLE}/stream/${SPOT_STREAMID} -p ${AWSPROFILE} >& streamS.new
#diff -b -B streamS.base streamS.new| awk -F"> " '{print $2}' > mrS.stream
#cat mrS.stream >> streamS.base
#python get_stream_data.py arn:aws:dynamodb:${REG}:${ACCT}:table/${GAMMATABLE}/stream/${GR_STREAMID} -p ${AWSPROFILE} >&  streamD.new
#diff -b -B streamD.base streamD.new| awk -F"> " '{print $2}' > mrD.stream
#cat mrD.stream >> streamD.base
#deactivate
#cd ${PREFIX}/tools/timings
#./cleanupDB.sh ${AWSPROFILE} ${PREFIX}
#/bin/sleep 30 #seconds

######micro########
#export COUNT=50
#echo; echo micro
#./micro.sh ${AWSPROFILE} ${COUNT} ${PREFIX}
#./cleanupDB.sh ${AWSPROFILE} ${PREFIX}
