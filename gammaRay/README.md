## GammaRay Demo

GammaRay is an extension to AWS Lambda and Xray to extract causal order relationships and performance data from multifunction AWS Lambda applications.  GammaRay is described in this paper: http://www.cs.ucsb.edu/sites/cs.ucsb.edu/files/docs/reports/paper\_8.pdf

The file RUN\_README walks you through all of the steps necessary for setting up multiple applications and microbenchmarks with GammaRay. 

This document details the steps to perform a simple GammaRay demo.  The symbol B (for both or hybrid configuration described in the paper) used in the scripts and below indicates the GammaRay version.  When referring to the GammaRay tables and streams we use the symbol D (for dynamic monitor table data) in some scripts.

* First time only setup
```
#setup an IAM group, user, and role with AdministratorAccess via the IAM console
#steps to do this are at the bottom of this document if needed
https://console.aws.amazon.com/iam/

#clone the repo
git clone git@github.com:MAYHEM-Lab/UCSBFaaS-Wrappers.git
cd UCSBFaaS-Wrappers
cp GammaRay.env.template GammaRay.env
#edit GammaRay.env and update all entries with XXX in them
source GammaRay.env  

#install the library updates for fleece v0.13.0
mkdir -p ${BFLEECEDIR}
cd ${BFLEECEDIR}
virtualenv venv --python=python3
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install 'fleece==0.13.0' --force-reinstall
cd ${BFLEECE}
patch -b < ${PREFIX}/gammaRay/xray0130lite.patch
deactivate

#install the local library for tools and testing
cd ${LOCALLIBDIR}  #this should be gammaRays directory for most 
virtualenv venv --python=python3
source venv/bin/activate
pip install 'fleece==0.13.0' --force-reinstall 
pip install 'boto3==1.4.7' --force-reinstall #used by apps/map-reduce/driver.py
pip install graphviz
pip install requests
deactivate
```

* Setup your environment each time
```
cd UCSBFaaS-Wrappers
source GammaRay.env  

#[Optional] clean out/refresh the database table that GammaRay uses
aws dynamodb delete-table --table-name ${GAMMATABLE} --profile ${AWSPROFILE}
#run this until it says gammaRays not found:
aws --profile ${AWSPROFILE} dynamodb describe-table --region ${REG} --table-name ${GAMMATABLE}

#wait 30 seconds then recreate it:
aws --profile ${AWSPROFILE} dynamodb create-table --region ${REG} --table-name ${GAMMATABLE} --attribute-definitions AttributeName=reqID,AttributeType=S --key-schema AttributeName=reqID,KeyType=HASH --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=20 --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
#run this until the JSON returned has a field "TableStatus" that says "ACTIVE":
aws --profile ${AWSPROFILE} dynamodb describe-table --region ${REG} --table-name ${GAMMATABLE}
#Do not continue until the JSON returned has a field "TableStatus" that says "ACTIVE"!
```

* Create (or update) the lambdas
```
cd ${LOCALLIBDIR}  #this should be gammaRays directory for most 
source venv/bin/activate
#deploy the lambdas (2 of them) in the first region
python setupApps.py -f ./imageProc.json -p ${AWSPROFILE} --no_spotwrap --spotFnsTableName ${GAMMATABLE} --spotFnsTableRegion ${REG} --gammaRay --turn_on_tracing
#and the 3rd lambda in the second region
python setupApps.py -f ./imageProcEast.json -p ${AWSPROFILE} --no_spotwrap --spotFnsTableName ${GAMMATABLE} --spotFnsTableRegion ${REG} --gammaRay --turn_on_tracing
deactivate
```

* Setup triggers (Lambda event sources)
```
deactivate
cd ${PREFIX}/tools
export IMG_DBSYNC_TRIGGER_TABLE_PREFIX=image-proc- 
export IMG_DBSYNC_FUNCTION_NAME_PREFIX=DBSyncPy
./make_imgproc_tables.sh ${IMG_DBSYNC_TRIGGER_TABLE_PREFIX} ${IMG_DBSYNC_FUNCTION_NAME_PREFIX} ${AWSPROFILE} ${REG} ${PREFIX}

deactivate
cd ${PREFIX}/tools
export EASTSYNC_TRIGGER_TABLE_PREFIX=eastSyncTable-
export EASTSYNC_FUNCTION_NAME_PREFIX=UpdateWebsite
./make_imgproc_tables.sh ${EASTSYNC_TRIGGER_TABLE_PREFIX} ${EASTSYNC_FUNCTION_NAME_PREFIX} ${AWSPROFILE} ${XREG} ${PREFIX}

#Next, upload a jpg image (any picture of something) to the $SPOTBKTWEST bucket in AWS S3 in a folder called imgProc with a file name d1.jpg
#make the bucket if you have not already:
aws --profile ${AWSPROFILE} s3 mb s3://${SPOTBKTWEST}
#cp the file
aws --profile ${AWSPROFILE} s3 cp d1.jpg s3://${SPOTBKTWEST}/imgProc/

```

* Run the app and gather the data
```
#download the latest stream (so that we can diff it to only consider this app) into streamD.base (this filename is hardcoded and used in get\_table\_and\_stream.sh below)"
cd ${PREFIX}/tools 
deactivate
./get_base_stream.sh ${PREFIX} ${AWSPROFILE} ${REG} ${GAMMATABLE}

cd ${PREFIX}/tools/timings
deactivate
export COUNT=2
./imageProc.sh ${AWSPROFILE} ${COUNT} ${PREFIX} ${REG} ${XREG} ${SPOTBKTWEST} ${IMG_DBSYNC_TRIGGER_TABLE_PREFIX} #IMG_DBSYNC_TRIGGER_TABLE_PREFIX without suffix

#process the stream data (happens offline in the background by a cloud platform service) but you can run it directly after running the app
export APP1=imageproc
cd ${PREFIX}/tools 
./get_table_and_stream.sh ${APP1} ${PREFIX} ${AWSPROFILE} ${REG} ${XREG} ${GAMMATABLE} ${SPOTTABLE} ${APP1}

cd ${LOCALLIBDIR}  
source venv/bin/activate
cd ${PREFIX}/tools
python stream_parser.py imageproc/imageprocD.new imageproc >& imageproc.out
python stream_parser.py --include_all_sdks imageproc/imageprocD.new imageproc >& imageproc.out
python stream_parser.py --aggregate --include_all_sdks imageproc/imageprocD.new imageproc >& imageproc.out
deactivate
```

* Cleanup everything 
```
#GammaRay tables if any
aws dynamodb delete-table --table-name ${GAMMATABLE} --profile ${AWSPROFILE}

#Cloudwatch logs
cd ${PREFIX}/tools/timings
./cleanupAWS.sh ${AWSPROFILE} ${REG} ${XREG}

#local log files 
export END=100
for i in $(seq 1 $END); do rm -rf ${PREFIX}/gammaRay/apps/${i}; done
for i in $(seq 1 $END); do rm -rf ${PREFIX}/gammaRay/apps/map-reduce/${i}; done
for i in $(seq 1 $END); do rm -rf ${PREFIX}/tools/dynamodb/${i}; done
for i in $(seq 1 $END); do rm -rf ${PREFIX}/tools/cloudwatch/${i}; done
for i in $(seq 1 $END); do rm -rf ${PREFIX}/tools/cloudwatch/logs/; done

#local app files
cd ${PREFIX}/tools
export APP1=imageproc
rm -rf ${APP1}*
aws --profile ${AWSPROFILE} s3 rm s3://${SPOTBKTWEST}/imgProc/d1.jpg

#Optional: delete all triggers
cd ${PREFIX}/gammaRay
deactivate
source venv/bin/activate
cd ${PREFIX}/tools
python cleanupEventSources.py ${AWSPROFILE} ${XREG} "UpdateWebsiteD"
python cleanupEventSources.py ${AWSPROFILE} ${REG} "DBSyncPyD:FnInvokerPyD"
deactivate

#Optional: delete all lambdas
cd ${PREFIX}/tools/timings
./cleanupLambdas.sh ${AWSPROFILE} ${AWSROLE} ${PREFIX}
```

* Other Setup Help   
Setup an IAM group, user, and role with AdministratorAccess via the IAM console

```
1) Create an IAM group
https://console.aws.amazon.com/iam/home?region=us-west-2#/groups/lamdagroup
Name: testgroup
<Create New Group>
Select AdministratorAccess
<Create Group>

2) Create a IAM user
https://console.aws.amazon.com/iam/home?region=us-west-2#/home
User name: testuser
Access type: select Programmatic access
Select group: testgroup
<Next>
<Create user>
<Download CSV>
extract access key and secret key and login url

add the creds for AWS CLI use (~/.aws/credentials)
[testuser]
aws_access_key_id = XXX
aws_secret_access_key = YYY

add config (~/.aws/config) for AWS CLI use #change the region to your default region
[profile testuser]
output = json
region = us-west-2 

3) Create a role
https://console.aws.amazon.com/iam/home?region=us-west-2#/roles
AWS Service = Lambda
<Next>
Select AdministratorAccess
<Next>
Name: testlambda

4) update Gammaray.env with the new names (testlambda and testuser) and source file

cd UCSBFaaS-Wrappers
#edit GammaRay.env and update
export ROLE=testlambda
export AWSPROFILE=testuser

source GammaRay.env  
```
