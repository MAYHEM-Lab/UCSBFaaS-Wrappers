#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name. Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset count (second var). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${3+x} ]; then echo 'Unset prefix as arg3 (full path to/including UCSBFaaS-Wrappers). Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
COUNT=$2
PREFIX=$3
LAMDIR=${PREFIX}/lambda-python
GRDIR=${PREFIX}/gammaRay
CWDIR=${PREFIX}/tools/cloudwatch
TOOLSDIR=${PREFIX}/tools/timings
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
TS=1401861965497 #some early date
REG=us-west-2

#create emptySbig by commenting out sys.exit(1) in setupApps.py after "Found boto" statement and run this:
#python setupApps.py -f configs/Sbig.json -p ${AWSPROFILE} --spotFnsTableName spotFns --spotFnsTableRegion ${REG}
#using the config at the bottom of this file as configs/Sbig.json; then run with nolibload in the event datastructure as done below

#FILELIST=( 
    #emptyS \
    #emptySbig \
    #emptyD \
#)
FILELIST=( 
    emptySbig \
)

cd ${GRDIR}
. ./venv/bin/activate
cd ${CWDIR}
	
for f in "${FILELIST[@]}"
do
    echo "processing: ${f}"
    python downloadLogs.py "/aws/lambda/${f}" ${TS} -p ${PROF} --deleteOnly
    for i in `seq 1 ${COUNT}`;
    do
        if [[ $f == emptySbig* ]] ;
        then
            aws lambda invoke --invocation-type Event --function-name ${f} --region ${REG} --profile ${PROF} --payload "{\"eventSource\":\"testing123\",\"nolibload\":\"yes\"}" outputfile
        else
            aws lambda invoke --invocation-type Event --function-name ${f} --region ${REG} --profile ${PROF} --payload "{}" outputfile
        fi
        /bin/sleep 30 #seconds
        mkdir -p $i/APIS/
        python downloadLogs.py "/aws/lambda/${f}" ${TS} -p ${PROF} > $i/APIS/${f}.log
    done
done
deactivate

###########cjk.json####################
#{
    #"region": "us-west-2",
    #"functions": [
        #{
            #"name": "emptySbig",
            #"lambdaMemory": 128,
            #"handler": "empty.handler",
            #"zip": "package.zip",
            #"files_and_dirs": [
                #"micro-benchmarks/empty.py",
                #"/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/boto144/venv/lib/python3.6/site-packages/botocore"
            #],
            #"patched_botocore_dir": "/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/boto144/venv/lib/python3.6/site-packages/botocore",
            #"s3bucket": "cjktestbkt"
        #}
    #]
#}

