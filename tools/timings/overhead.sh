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
python downloadLogs.py "/aws/lambda/mapper" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/reducer" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/driver" 1401861965497 -p cjk1 --deleteOnly
python downloadLogs.py "/aws/lambda/reducerCoordinator" 1401861965497 -p cjk1 --deleteOnly
deactivate

for i in `seq 1 10`;
do
    #delete the bucket contents for the job
    aws s3 rm s3://spot-mr-bkt/job3000 --recursive --profile cjk1

    cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/lambda-python/mr
    . ../venv/bin/activate
    #run the driver
    rm -f overhead.out
    /usr/bin/time python driver.py spot-mr-bkt job3000 mapper reducer --wait4reducers >> overhead.out
    mkdir -p $i
    mv overhead.out $i/

    #download cloudwatch logs (and delete them)
    cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/cloudwatch
    mkdir -p $i
    python downloadLogs.py "/aws/lambda/mapper" 1401861965497 -p cjk1 --delete  > $i/map.log
    python downloadLogs.py "/aws/lambda/reducer" 1401861965497 -p cjk1 --delete  > $i/red.log
    python downloadLogs.py "/aws/lambda/driver" 1401861965497 -p cjk1 --delete  > $i/driv.log
    python downloadLogs.py "/aws/lambda/reducerCoordinator" 1401861965497 -p cjk1 --delete  > $i/coord.log
    deactivate
    
    #download the db and then delete its entries
    cd /Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers/tools/dynamodb
    . ./venv/bin/activate
    rm -rf dump
    python dynamodump.py -m backup -r us-west-2 -p cjk1 -s spotFns
    mkdir -p $i
    mv dump $i/
    python dynamodelete.py -p cjk1 spotFns
    deactivate
done
