#! /bin/bash

#delete db entries
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/dynamodb
. ./venv/bin/activate
python dynamodelete.py -p cjk1 spotFns
deactivate
#delete the logs
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/lambda-python
. ./venv/bin/activate
cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/cloudwatch
python downloadLogs.py "/aws/lambda/mapperNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/reducerNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/driverNS" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinatorNS" 1401861965497 -p cjk1 --deleteOnly
deactivate

#do the same for no spotwrap
for i in `seq 1 10`;
do
    #delete the bucket contents for the job
    aws s3 rm s3://spot-mr-bkt-ns/jobNS300 --recursive --profile cjk1

    cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/lambda-python/mr
    rm -f overhead.out
    . ../venv/bin/activate
    #run the driver
    /usr/bin/time python driver.py spot-mr-bkt-ns jobNS300 mapperNS reducerNS --wait4reducers >> overhead.out
    mkdir -p $i/NS
    mv overhead.out $i/NS

    #download cloudwatch logs (and delete them)
    cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/cloudwatch
    mkdir -p $i/NS
    python downloadLogs.py "/aws/lambda/mapperNS" 1401861965497 -p cjk1 --delete  > $i/NS/map.log
    python downloadLogs.py "/aws/lambda/reducerNS" 1401861965497 -p cjk1 --delete  > $i/NS/red.log
    python downloadLogs.py "/aws/lambda/driverNS" 1401861965497 -p cjk1 --delete  > $i/NS/driv.log
    python downloadLogs.py "/aws/lambda/reducerCoordinatorNS" 1401861965497 -p cjk1 --delete  > $i/NS/coord.log
    deactivate
    
    #download the db and then delete its entries
    cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/dynamodb
    . ./venv/bin/activate
    rm -rf dump
    python dynamodump.py -m backup -r us-west-2 -p cjk1 -s spotFns
    mkdir $i/NS
    mv dump $i/NS/
    python dynamodelete.py -p cjk1 spotFns
    deactivate
done
