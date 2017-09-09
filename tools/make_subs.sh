#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset AWS profile name (arg1). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset AWS account (arg2). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${3+x} ]; then echo 'Unset AWS region in which lambda is in (arg3). Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
PREFIX=$2
REG=$3
LAMBDANAME=S3ModPy
TOPICNAME=topic
#SUFFIXLIST=( 
    #B \
#)
SUFFIXLIST=( 
    C \
    F \
    T \
    S \
    D \
    B \
)
for suffix in "${SUFFIXLIST[@]}"
do
    TOPIC=${TOPICNAME}${suffix}
    LAMBDA=${LAMBDANAME}${suffix}
    aws sns create-topic --name ${TOPIC} --profile ${PROF} --region ${REG}
    aws lambda add-permission --function-name ${LAMBDA} --statement-id ${LAMBDA} --action "lambda:InvokeFunction" --principal sns.amazonaws.com --source-arn arn:aws:sns:us-west-2:${ACCT}:${TOPIC} --profile ${PROF} --region ${REG}
    echo "***** Note: if the above failed on ResourceConflictException, you can disregard (permission is already set)"
    aws sns subscribe --topic-arn arn:aws:sns:us-west-2:${ACCT}:${TOPIC} --protocol lambda --notification-endpoint arn:aws:lambda:${REG}:${ACCT}:function:${LAMBDA} --profile ${PROF} --region ${REG}
done
