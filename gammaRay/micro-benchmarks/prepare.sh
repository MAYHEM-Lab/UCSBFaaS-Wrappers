if [ -z ${1+x} ]; then echo 'Unset S3BKT (arg1). Set and rerun. Exiting.  ..!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset DYNAMODB tablename (arg2). Set and rerun. Exiting.  ..!'; exit 1; fi
S3BKT=$1
DYNAMODB=$2
touch file
for i in `seq 101 1000`;
do
aws s3 cp file s3://${S3BKT}/$i/file;
aws dynamodb put-item --table-name ${DYNAMODB} --item {\"id\":{\"N\":\"$i\"}}
sleep 2
done

