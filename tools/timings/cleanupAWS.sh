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
/aws/lambda/mapper \
/aws/lambda/reducer \
/aws/lambda/driver \
/aws/lambda/reducerCoordinator \
/aws/lambda/mapperNS \
/aws/lambda/reducerNS \
/aws/lambda/driverNS \
/aws/lambda/reducerCoordinatorNS \
/aws/lambda/mapperGR \
/aws/lambda/reducerGR \
/aws/lambda/driverGR \
/aws/lambda/reducerCoordinatorGR \
/aws/lambda/mapperF \
/aws/lambda/reducerF \
/aws/lambda/driverF \
/aws/lambda/reducerCoordinatorF \
/aws/lambda/SNSPy \
/aws/lambda/S3ModPy \
/aws/lambda/DBModPy \
/aws/lambda/DBSync \
/aws/lambda/DBSyncPy \
/aws/lambda/FnInvokerPy \
/aws/lambda/SpotTemplatePy \
/aws/lambda/SNSPyNS \
/aws/lambda/S3ModPyNS \
/aws/lambda/DBModPyNS \
/aws/lambda/FnInvokerPyNS \
/aws/lambda/SpotTemplatePyNS \
/aws/lambda/ImageProcPy \
/aws/lambda/ImageProcPyNDB \
/aws/lambda/ImageProc_F_Py \
/aws/lambda/ImageProc_NGR_Py \
/aws/lambda/ImageProc_S_Py \
/aws/lambda/mapperD \
/aws/lambda/reducerD \
/aws/lambda/driverD \
/aws/lambda/reducerCoordinatorD \
/aws/lambda/SNSPyD \
/aws/lambda/S3ModPyD \
/aws/lambda/DBModPyD \
/aws/lambda/DBSyncPyD \
/aws/lambda/FnInvokerPyD \
/aws/lambda/ImageProcPyD \
/aws/lambda/mapperB \
/aws/lambda/reducerB \
/aws/lambda/driverB \
/aws/lambda/reducerCoordinatorB \
/aws/lambda/SNSPyB \
/aws/lambda/S3ModPyB \
/aws/lambda/DBModPyB \
/aws/lambda/DBSyncPyB \
/aws/lambda/FnInvokerPyB \
/aws/lambda/ImageProcPyB \
/aws/lambda/SNSPyF \
/aws/lambda/S3ModPyF \
/aws/lambda/DBModPyF \
/aws/lambda/DBSyncPyF \
/aws/lambda/FnInvokerPyF \
/aws/lambda/ImageProcPyF \
/aws/lambda/mapperT \
/aws/lambda/reducerT \
/aws/lambda/driverT \
/aws/lambda/reducerCoordinatorT \
/aws/lambda/SNSPyT \
/aws/lambda/S3ModPyT \
/aws/lambda/DBModPyT \
/aws/lambda/DBSyncPyT \
/aws/lambda/FnInvokerPyT \
/aws/lambda/ImageProcPyT \
/aws/lambda/mapperS \
/aws/lambda/reducerS \
/aws/lambda/driverS \
/aws/lambda/reducerCoordinatorS \
/aws/lambda/SNSPyS \
/aws/lambda/S3ModPyS \
/aws/lambda/DBModPyS \
/aws/lambda/DBSyncPyS \
/aws/lambda/FnInvokerPyS \
/aws/lambda/ImageProcPyS \
/aws/lambda/mapperD \
/aws/lambda/reducerD \
/aws/lambda/driverD \
/aws/lambda/reducerCoordinatorD \
/aws/lambda/SNSPyD \
/aws/lambda/S3ModPyD \
/aws/lambda/DBModPyD \
/aws/lambda/DBSyncPyD \
/aws/lambda/mapperC \
/aws/lambda/reducerC \
/aws/lambda/driverC \
/aws/lambda/reducerCoordinatorC \
/aws/lambda/SNSPyC \
/aws/lambda/S3ModPyC \
/aws/lambda/DBModPyC \
/aws/lambda/DBSyncPyC \
/aws/lambda/FnInvokerPyC \
/aws/lambda/ImageProcPyC \
/aws/lambda/UpdateWebsiteC \
/aws/lambda/UpdateWebsiteT \
/aws/lambda/UpdateWebsiteF \
/aws/lambda/UpdateWebsiteS \
/aws/lambda/UpdateWebsiteD \
/aws/lambda/UpdateWebsiteB \
/aws/lambda/dbreadC \
/aws/lambda/dbreadT \
/aws/lambda/dbreadF \
/aws/lambda/dbreadS \
/aws/lambda/dbreadD \
/aws/lambda/dbwriteC \
/aws/lambda/dbwriteT \
/aws/lambda/dbwriteF \
/aws/lambda/dbwriteS \
/aws/lambda/dbwriteD \
/aws/lambda/emptyC \
/aws/lambda/emptyT \
/aws/lambda/emptyF \
/aws/lambda/emptyS \
/aws/lambda/emptyD \
/aws/lambda/emptyB \
/aws/lambda/emptySbig \
/aws/lambda/pubsnsC \
/aws/lambda/pubsnsT \
/aws/lambda/pubsnsF \
/aws/lambda/pubsnsS \
/aws/lambda/pubsnsD \
/aws/lambda/pubsnsB \
/aws/lambda/s3readC \
/aws/lambda/s3readT \
/aws/lambda/s3readF \
/aws/lambda/s3readS \
/aws/lambda/s3readD \
/aws/lambda/s3readB \
/aws/lambda/s3writeC \
/aws/lambda/s3writeT \
/aws/lambda/s3writeF \
/aws/lambda/s3writeS \
/aws/lambda/s3writeD \
/aws/lambda/s3writeB \
/aws/lambda/S3EventProcessor \
/aws/lambda/UploadObjectToS3 \
)

for f in "${LLIST[@]}"
do
    echo "processing ${f}"
    if [[ ${lambda} == UpdateWeb* ]] ;
    then
        aws logs delete-log-group --region ${XREG} --profile ${PROF} --log-group-name ${f}
    else
        aws logs delete-log-group --region ${REG} --profile ${PROF} --log-group-name ${f}
    fi
done
