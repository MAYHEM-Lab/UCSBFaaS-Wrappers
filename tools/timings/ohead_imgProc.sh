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
python downloadLogs.py "/aws/lambda/ImageProcPy" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProcPyNDB" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProc_F_Py" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProc_NGR_Py" ${TS} -p ${PROF} --deleteOnly
python downloadLogs.py "/aws/lambda/ImageProc_S_Py" ${TS} -p ${PROF} --deleteOnly

for i in `seq 1 100`;
do
#run via (changing the function name as appropriate)
aws lambda invoke --invocation-type Event --function-name ImageProcPy --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","name":"cjktestbkt","key":"imgProc/d1.jpg"}' outputfile
aws lambda invoke --invocation-type Event --function-name ImageProcPyNDB --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","name":"cjktestbkt","key":"imgProc/d1.jpg"}' outputfile
aws lambda invoke --invocation-type Event --function-name ImageProc_F_Py --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","name":"cjktestbkt","key":"imgProc/d1.jpg"}' outputfile
aws lambda invoke --invocation-type Event --function-name ImageProc_NGR_Py --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","name":"cjktestbkt","key":"imgProc/d1.jpg"}' outputfile
aws lambda invoke --invocation-type Event --function-name ImageProc_S_Py --region us-west-2 --profile cjk1 --payload '{"eventSource":"ext:invokeCLI","name":"cjktestbkt","key":"imgProc/d1.jpg"}' outputfile
done
/bin/sleep 120 #seconds, so 2mins - wait for logs to be written

cd ${CWDIR}
mkdir -p logs
TS=1401861965497 #some early date
PROF=cjk1
python downloadLogs.py "/aws/lambda/ImageProcPy" ${TS} -p ${PROF} > logs/ippNew.log
python downloadLogs.py "/aws/lambda/ImageProcPyNDB" ${TS} -p ${PROF} > logs/ippndb.log
python downloadLogs.py "/aws/lambda/ImageProc_F_Py" ${TS} -p ${PROF} > logs/ippf.log
python downloadLogs.py "/aws/lambda/ImageProc_NGR_Py" ${TS} -p ${PROF} > logs/ippngr.log
python downloadLogs.py "/aws/lambda/ImageProc_S_Py" ${TS} -p ${PROF} > logs/ipps.log
deactivate
