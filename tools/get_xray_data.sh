#! /bin/bash
NUM_ARGS=5
display_usage() { 
    echo "./get_xray_data.sh APPNAME PREFIX awsprofile region output_dir"
    echo "If your GammaRay environment is set you can export APP1 as APPNAME and use"
    echo "./get_table_and_stream.sh \${APP1} \${PREFIX} \${AWSPROFILE} \${REG} output_dir"
} 
if [  $# -ne ${NUM_ARGS} ] 
then 
    display_usage
    exit 1
fi
APP1=$1
PREFIX=$2
PROF=$3
REG=$4
OUT=$5
TOOLSDIR=${PREFIX}/tools
cd ${TOOLSDIR}

DSTART=`date "+%Y-%m-%dT%H:%M:%S"` #not utc so 7 hours earlier
DEND=`date -u "+%Y-%m-%dT%H:%M:%S"` #utc
echo $REG
TIDS=$(aws xray get-trace-summaries --no-sampling --region ${REG} --profile ${PROF} --start-time ${DSTART} --end-time ${DEND} --query 'TraceSummaries[*].Id' --output text)
#echo $TIDS

mkdir -p ${OUT}
for TID in ${TIDS}  #one per trace ID, only request it if we don't yet have it
do
    FNAME=${APP1}B_${TID}.xray
    if [ ! -f ${FNAME} ]; then
        aws xray batch-get-traces --region ${REG} --profile ${PROF} --trace-ids ${TID} > ${FNAME}
        cp ${FNAME} ${OUT}
    fi
done

