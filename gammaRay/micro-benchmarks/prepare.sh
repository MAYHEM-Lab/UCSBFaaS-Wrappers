S3BKT=cjk-apitest-bucket
DYNAMODB=noTriggerTestTable
touch file
for i in `seq 101 1000`;
do
aws s3 cp file s3://${S3BKT}/$i/file;
aws dynamodb put-item --table-name ${DYNAMODB} --item {\"id\":{\"N\":\"$i\"}}
sleep 2
done

