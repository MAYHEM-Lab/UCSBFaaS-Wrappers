S3BKT=apitest-bucket
DYNAMODB=swtest_read
touch file
for i in `seq 1 100`;
do
aws s3 cp file s3://${S3BKT}/$i/file;
aws dynamodb put-item --table-name ${DYNAMODB} --item {\"id\":{\"N\":\"$i\"}}
done

