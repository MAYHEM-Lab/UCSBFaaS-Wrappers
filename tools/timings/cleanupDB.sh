#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset aws_profile (arg1). Set and rerun. Exiting...!'; exit 1; fi
if [ -z ${2+x} ]; then echo 'Unset prefix as arg2 (full path to/including UCSBFaaS-Wrappers). Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
PREFIX=$2
GRDIR=${PREFIX}/gammaRay
DYNDBDIR=${PREFIX}/tools/dynamodb
SPOTTABLE=spotFns #must match tablename used by SpotWrap.py.template
GAMMATABLE=gammaRays #must match tablename used by SpotWrap.py.template

#delete dynamodb entries in table ${SPOTTABLE}
cd ${GRDIR}
. venv/bin/activate
cd ${DYNDBDIR}
python dynamodelete.py -p ${PROF} ${SPOTTABLE}
python dynamodelete.py -p ${PROF} ${GAMMATABLE}
