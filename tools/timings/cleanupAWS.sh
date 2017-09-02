#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset args. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
MRBKT=spot-mr-bkt #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run without --no_spotwrap
MRBKTNS=spot-mr-bkt-ns #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
MRBKTGR=spot-mr-bkt-gr #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
MRBKTF=spot-mr-bkt-f #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
LAMDIR=${PREFIX}/lambda-python
DYNDBDIR=${PREFIX}/tools/dynamodb
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
MRDIR=${PREFIX}/lambda-python/mr
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
GAMMATABLE=gammaRays #must match tablename used by SpotWrap.py.template
TS=1401861965497 #some early date

cd ${TOOLSDIR}
#delete s3 entries for map/reduce jobs
aws s3 rm s3://${MRBKT}/ --recursive --profile ${PROF}
aws s3 rm s3://${MRBKTNS}/ --recursive --profile ${PROF}
aws s3 rm s3://${MRBKTGR}/ --recursive --profile ${PROF}
aws s3 rm s3://${MRBKTF}/ --recursive --profile ${PROF}
#delete dynamodb entries in table ${SPOTTABLE}
cd ${LAMDIR}
. venv/bin/activate
cd ${DYNDBDIR}
python dynamodelete.py -p ${PROF} ${SPOTTABLE}
python dynamodelete.py -p ${PROF} ${GAMMATABLE}
deactivate
#delete the logs for the lambdas with spotwrap and without (NS)
cd ${MRDIR}
. ../venv/bin/activate
cd ${CWDIR}
python downloadLogs.py "/aws/lambda/mapper" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducer" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/driver" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinator" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/mapperNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/driverNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinatorNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/mapperGR" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerGR" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/driverGR" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinatorGR" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/mapperF" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerF" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/driverF" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinatorF" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/SNSPy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/S3ModPy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/DBModPy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/DBSync" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/FnInvokerPy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/SpotTemplatePy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/SNSPyNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/S3ModPyNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/DBModPyNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/FnInvokerPyNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/SpotTemplatePyNS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProcPy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProcPyNDB" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProc_F_Py" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProc_NGR_Py" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProc_S_Py" ${TS} -p ${PROF} --deleteOnly
deactivate

cd ${TOOLSDIR}

