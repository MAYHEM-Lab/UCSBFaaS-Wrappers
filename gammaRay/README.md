## GammaRay Demo

GammaRay is an extension to AWS Lambda and Xray to extract causal order relationships and performance data from multifunction AWS Lambda applications.

The file RUN\_README walks you through all of the steps necessary for setting up multiple applications and microbenchmarks with GammaRay. 

This document details the steps to perform a simple GammaRay demo.

* First time only setup
```
git clone git@github.com:MAYHEM-Lab/UCSBFaaS-Wrappers.git
cd UCSBFaaS-Wrappers
cp GammaRay.env GammaRay.env
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
deactivate
```

* Setup your environment each time
```
cd UCSBFaaS-Wrappers
source GammaRay.env  

#[Optional] clean out/refresh the database table that GammaRay uses
aws dynamodb delete-table --table-name ${GAMMATABLE} --profile ${AWSPROFILE}
#wait 30 seconds then recreate it:
aws --profile ${AWSPROFILE} dynamodb create-table --region ${REG} --table-name ${GAMMATABLE} --attribute-definitions AttributeName=reqID,AttributeType=S --key-schema AttributeName=reqID,KeyType=HASH --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=20 --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
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
aws --profile ${AWSPROFILE} s3 cp d1.jpg s3://${SPOTBKTWEST}/imgProc/
```

* Run the app and gather the data
```
cd ${PREFIX}/tools/timings
deactivate
export COUNT=1
./imageProc.sh ${AWSPROFILE} ${COUNT} ${PREFIX} ${REG} ${XREG} ${SPOTBKTWEST} ${IMG_DBSYNC_TRIGGER_TABLE_PREFIX} #IMG_DBSYNC_TRIGGER_TABLE_PREFIX without suffix

#process the stream data (happens offline in the background by a cloud platform service) but you can run it directly after running the app
export APP1=imageproc
cd ${PREFIX}/tools 
./get_table_and_stream.sh ${APP1} ${PREFIX} ${AWSPROFILE} ${REG} ${GAMMATABLE} ${SPOTTABLE}

cd ${LOCALLIBDIR}  
source venv/bin/activate
cd ${PREFIX}/tools
mkdir backup
cp *.xray backup
python stream_parser.py streamD.new --hybrid backup
deactivate
```

* Cleanup everything 
```
#GammaRay tables if any
aws dynamodb delete-table --table-name ${SPOTTABLE} --profile ${AWSPROFILE}
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

#Optional: all lambdas
./cleanupLambdas.sh ${AWSPROFILE} ${AWSROLE} ${PREFIX}
```

