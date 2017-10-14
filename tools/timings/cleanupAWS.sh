#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset aws_profile (arg1). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset region (arg2). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${3+x} ]; then echo 'Unset cross-region name (arg3). Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
REG=$2 #us-west-2
XREG=$3 #us-east-1

#delete s3 entries for map/reduce jobs
MRBKT=spot-mr-bkt #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run without --no_spotwrap
MRBKTNS=spot-mr-bkt-ns #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
MRBKTGR=spot-mr-bkt-gr #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
MRBKTF=spot-mr-bkt-f #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
MRBKTT=spot-mr-bkt-t #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
MRBKTT=spot-mr-bkt-b #must match reducerCoordinator "permission" in setupconfig.json when setupApps.py is run with --no_spotwrap
aws s3 rm s3://${MRBKT}/ --recursive --profile ${PROF}
aws s3 rm s3://${MRBKTNS}/ --recursive --profile ${PROF}
aws s3 rm s3://${MRBKTGR}/ --recursive --profile ${PROF}
aws s3 rm s3://${MRBKTF}/ --recursive --profile ${PROF}
aws s3 rm s3://${MRBKTT}/ --recursive --profile ${PROF}

#delete log groups for all lambdas, errors can be ignored
LLIST=(
#/aws/lambda/mapperB \
#/aws/lambda/reducerB \
#/aws/lambda/driverB \
#/aws/lambda/reducerCoordinatorB \
#/aws/lambda/SNSPyB \
#/aws/lambda/S3ModPyB \
#/aws/lambda/DBModPyB \
#/aws/lambda/FnInvokerPyB \
/aws/lambda/DBSyncPyB \
/aws/lambda/ImageProcPyB \
#/aws/lambda/mapperC \
#/aws/lambda/reducerC \
#/aws/lambda/driverC \
#/aws/lambda/reducerCoordinatorC \
#/aws/lambda/SNSPyC \
#/aws/lambda/S3ModPyC \
#/aws/lambda/DBModPyC \
#/aws/lambda/DBSyncPyC \
#/aws/lambda/FnInvokerPyC \
#/aws/lambda/ImageProcPyC \
#/aws/lambda/UpdateWebsiteC \
/aws/lambda/UpdateWebsiteB \
#/aws/lambda/dbreadC \
#/aws/lambda/dbreadB \
#/aws/lambda/dbwriteC \
#/aws/lambda/dbwriteB \
#/aws/lambda/emptyC \
#/aws/lambda/emptyB \
#/aws/lambda/emptySbig \
#/aws/lambda/pubsnsC \
#/aws/lambda/pubsnsB \
#/aws/lambda/s3readC \
#/aws/lambda/s3readB \
#/aws/lambda/s3writeC \
#/aws/lambda/s3writeB \
)

for lambda in "${LLIST[@]}"
do
    if [[ ${lambda} == *"UpdateWeb"* ]] ;
    then
        echo "processing region ${XREG} ${lambda}"
        aws logs delete-log-group --region ${XREG} --profile ${PROF} --log-group-name ${lambda}
    else
        echo "processing region ${REG} ${lambda}"
        aws logs delete-log-group --region ${REG} --profile ${PROF} --log-group-name ${lambda}
    fi
done
