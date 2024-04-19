#!/bin/sh
SCRIPT_DIR=`dirname $0`
cd $SCRIPT_DIR && cd .. || exit 1

source bin/environ.sh

celery -A config.prod worker -Q er_execute,er_schedule -l info
