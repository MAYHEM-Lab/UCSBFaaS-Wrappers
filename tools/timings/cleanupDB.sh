#! /bin/bash
if [ -z ${1+x} ]; then echo 'Unset args. Set and rerun. Exiting...!'; exit 1; fi
PROF=$1
PREFIX=/Users/ckrintz/RESEARCH/lambda/UCSBFaaS-Wrappers
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
