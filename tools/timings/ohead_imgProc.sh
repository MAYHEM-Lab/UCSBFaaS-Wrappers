#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
TS=1401861965497 #some early date
PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
GAMDIR=${PREFIX}/gammaRay
LAMDIR=${PREFIX}/lambda-python
CWDIR=${PREFIX}/tools/cloudwatch
cd ${LAMDIR}
. ./venv/bin/activate
cd ${CWDIR}
python downloadLogs.py "/aws/lambda/ImageProcPyS" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProcPyC" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProcPyD" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProcPyT" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProcPyF" ${TS} -p ${PROF} --deleteOnly

for i in `seq 1 100`;
do
#run via (changing the function name as appropriate)
aws lambda invoke --invocation-type Event --function-name ImageProcPyC --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","name":"cjktestbkt","key":"imgProc/d1.jpg"}' outputfile
aws lambda invoke --invocation-type Event --function-name ImageProcPyS --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","name":"cjktestbkt","key":"imgProc/d1.jpg"}' outputfile
aws lambda invoke --invocation-type Event --function-name ImageProcPyD --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","name":"cjktestbkt","key":"imgProc/d1.jpg"}' outputfile
aws lambda invoke --invocation-type Event --function-name ImageProcPyF --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","name":"cjktestbkt","key":"imgProc/d1.jpg"}' outputfile
aws lambda invoke --invocation-type Event --function-name ImageProcPyT --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","name":"cjktestbkt","key":"imgProc/d1.jpg"}' outputfile
/bin/sleep 10 #seconds
done
/bin/sleep 120 #seconds, so 2mins - wait for logs to be written

cd ${CWDIR}
mkdir -p logs
TS=1401861965497 #some early date
PROF=cjk1
python downloadLogs.py "/aws/lambda/ImageProcPyS" ${TS} -p ${PROF} > logs/ippS.log
python downloadLogs.py "/aws/lambda/ImageProcPyC" ${TS} -p ${PROF} > logs/ippC.log
python downloadLogs.py "/aws/lambda/ImageProcPyD" ${TS} -p ${PROF} > logs/ippD.log
python downloadLogs.py "/aws/lambda/ImageProcPyT" ${TS} -p ${PROF} > logs/ippT.log
python downloadLogs.py "/aws/lambda/ImageProcPyF" ${TS} -p ${PROF} > logs/ippF.log
deactivate
