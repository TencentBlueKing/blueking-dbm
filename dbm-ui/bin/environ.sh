#!/bin/sh

export APP_ID="bk_dbm"
export APP_TOKEN="xxxxxx"
export DJANGO_SETTINGS_MODULE=config.prod
export BK_LOG_DIR=/tmp/bk-dbm
export BK_IAM_SKIP=true
export DBA_APP_BK_BIZ_ID=0
export DB_NAME="bk_dbm"
export REPORT_DB_NAME="bk_dbm_report"
export PYTHON_VERSION="${PYTHON_VERSION:-3.6}"
