#! /bin/bash
NUM_ARGS=4
display_usage() { 
    echo "./get_base_stream.sh PREFIX awsprofile region1 DTABLE"
    echo "This program creates a file called streamD.base which is a snapshot of the current DTABLE stream"
} 
if [  $# -ne ${NUM_ARGS} ] 
then 
    display_usage
    exit 1
fi
PREFIX=$1
PROF=$2
REG=$3
DTABLE=$4
GRDIR=${PREFIX}/gammaRay
TOOLSDIR=${PREFIX}/tools

cd ${GRDIR}
source venv/bin/activate
cd ${TOOLSDIR}

TMPFILE=tmp_file.out
aws dynamodb describe-table --region ${REG} --table-name ${DTABLE} --profile ${PROF} > ${TMPFILE}
DARN=`python getEleFromJson.py Table:LatestStreamArn ${TMPFILE}`
rm -f ${TMPFILE}

python get_stream_data.py ${DARN} -p ${PROF} >  streamD.base

