#!/bin/sh

SCRIPT_DIR=`dirname $0`
./bin/manage.sh migrate --database=report_db
./bin/manage.sh migrate