#! /bin/bash
NUM_ARGS=5
display_usage() { 
    echo "./make_tables.sh DYNAMODB_TABLENAME_PREFIX LAMBDA_FUNCTION_NAME_PREFIX awsprofile region REPO_PREFIX"
    echo "C,T,F,S,D, and B suffixes will be appended to both prefixes to construct table and function names"
    echo "This script deletes the table names and recreates them (primary_key=String id)"
    echo "It then assigns the table as the trigger for the corresponding function name (same suffix)"
} 
if [  $# -lt ${NUM_ARGS} ] 
then 
    display_usage
    exit 1
fi
TBL_PREF=$1
LAM_PREF=$2
PROF=$3
REG=$4
PREFIX=$5
GRDIR=${PREFIX}/gammaRay
TOOLSDIR=${PREFIX}/tools

SUFFIXES=( 
    C T F D S B \
)
cd ${GRDIR}
. ./venv/bin/activate
cd ${TOOLSDIR}

TMPFILE=tmp_imp.out
COUNT=10
for suf in "${SUFFIXES[@]}"
do
    TABLE=${TBL_PREF}${suf}
    LAMBDA=${LAM_PREF}${suf}
    echo "processing ${TABLE} table and lambda: ${LAMBDA}"
    echo "deleting table (ResourceNotFoundException can be ignored)..."
    aws dynamodb delete-table --region ${REG} --table-name ${TABLE} --profile ${PROF} >&  /dev/null
    while :
    do
        /bin/sleep 5 #seconds
        aws dynamodb describe-table --region ${REG} --table-name ${TABLE} --profile ${PROF} >& /dev/null
        result="$?"
        if [ "$result" -ne 0 ]; then #loop until you get a ResourceNotFoundException error
            echo 'table deleted!'
            break
        fi
    done

    rm -f ${TMPFILE}
    echo "creating table ..."
    aws dynamodb create-table --region ${REG} --table-name ${TABLE} --attribute-definitions AttributeName=id,AttributeType=S --key-schema AttributeName=id,KeyType=HASH --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES --profile ${PROF} > ${TMPFILE}

    echo "extracting ARN ..."
    ARN=`python getEleFromJson.py TableDescription:LatestStreamArn ${TMPFILE}`

    echo "creating source event using ARN: ${ARN}"
    aws lambda create-event-source-mapping --region ${REG} --function-name ${LAMBDA} --event-source ${ARN} --batch-size 1 --starting-position TRIM_HORIZON --profile ${PROF} >& /dev/null
    result="$?"
    if [ "$result" -ne 0 ]; then 
        echo 'some error occured in create-event-source-mapping, remove the /dev/null and retry to see the error!'
    fi

done
deactivate
