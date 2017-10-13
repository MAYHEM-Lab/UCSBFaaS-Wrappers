#! /bin/bash
NUM_ARGS=8
display_usage() { 
    echo "./get_table_and_stream.sh APPNAME PREFIX awsprofile region1 region2 DTABLE STABLE output_dir"
    echo "If your GammaRay environment is set you can export APP1 as APPNAME and use"
    echo "If you only want one region put its name in for both region1 and region2"
    echo "./get_table_and_stream.sh \${APP1} \${PREFIX} \${AWSPROFILE} \${REG} \${XREG} \${GAMMATABLE} \${SPOTTABLE} output_dir"
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
XREG=$5
DTABLE=$6
STABLE=$7
OUT=$8
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

#get xray data for the two regions and put it in $OUT, only files not yet downloaded are downloaded
./get_xray_data.sh ${APP1} ${PREFIX} ${AWSPROFILE} ${REG} ${OUT}
./get_xray_data.sh ${APP1} ${PREFIX} ${AWSPROFILE} ${XREG} ${OUT}

