#! /bin/bash
NUM_ARGS=7
display_usage() { 
    echo "./get_table_and_stream.sh APPNAME PREFIX awsprofile region accountNo DTABLE STABLE"
    echo "If your GammaRay environment is set you can export APP1 as APPNAME and use"
    echo "./get_table_and_stream.sh \${APP1} \${PREFIX} \${AWSPROFILE} \${REG} \${GAMMATABLE} \${SPOTTABLE} output_dir"
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
DTABLE=$5
STABLE=$6
OUT=$7
GRDIR=${PREFIX}/gammaRay
TOOLSDIR=${PREFIX}/tools

#uncomment all that follow to dump the full database
#cd ${TOOLSDIR}/dynamodb
#source venv2.7/bin/activate
#rm -rf dump dump.${APP1}
#python dynamodump.py -m backup -r ${REG} -p ${PROF} -s ${STABLE}
#python dynamodump.py -m backup -r ${REG} -p ${PROF} -s ${DTABLE}
#mv dump dump.${APP1}
#deactivate

cd ${TOOLSDIR}/timings
./cleanupDB.sh ${PROF} ${PREFIX}

cd ${GRDIR}
source venv/bin/activate
cd ${TOOLSDIR}

TMPFILE=tmp_file.out
aws dynamodb describe-table --region ${REG} --table-name ${DTABLE} --profile ${PROF} > ${TMPFILE}
DARN=`python getEleFromJson.py Table:LatestStreamArn ${TMPFILE}`
aws dynamodb describe-table --region ${REG} --table-name ${STABLE} --profile ${PROF} > ${TMPFILE}
SARN=`python getEleFromJson.py Table:LatestStreamArn ${TMPFILE}`
rm -f ${TMPFILE}

mkdir -p ${OUT}
touch streamS.base streamD.base
python get_stream_data.py ${SARN} -p ${PROF} > streamS.new
python get_stream_data.py ${DARN} -p ${PROF} >  streamD.new
diff -b -B streamS.base streamS.new | awk -F"> " '{print $2}' > ${APP1}S.stream
cp streamS.new ${OUT}/${APP1}S.new
cat ${APP1}S.stream >> streamS.base
diff -b -B streamD.base streamD.new | awk -F"> " '{print $2}' > ${APP1}D.stream
cp streamD.new ${OUT}/${APP1}D.new
cat ${APP1}D.stream >> streamD.base

DSTART=`date "+%Y-%m-%dT%H:%M:%S"` #not utc so 7 hours earlier
DEND=`date -u "+%Y-%m-%dT%H:%M:%S"` #utc
aws --profile ${PROF} xray get-trace-summaries --start-time ${DSTART} --end-time ${DEND}  > ${TMPFILE}
TIDS=`python getEleFromJson.py TraceSummaries:Id ${TMPFILE} --multiple`
#echo ${TIDS}

#example for XRay download service: download between 1 and 2 minutes in the past
#EPOCH=$(date +%s)
#aws xray get-trace-summaries --start-time $(($EPOCH-120)) --end-time $(($EPOCH-60))

for TID in ${TIDS}  #one per trace ID, only request it if we dont yet have it
do
    FNAME=${APP1}B_${TID}.xray
    if [ ! -f ${FNAME} ]; then
        aws --profile ${PROF} xray batch-get-traces --trace-ids ${TID} > ${FNAME}
        cp ${FNAME} ${OUT}
    fi
done
rm -f ${TMPFILE}
