#!/bin/sh
SCRIPT_DIR=`dirname $0`
cd $SCRIPT_DIR && cd .. || exit 1

source bin/environ.sh

${PYTHON_BIN:-python} manage.py $@
