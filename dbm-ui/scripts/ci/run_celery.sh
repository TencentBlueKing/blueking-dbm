#!/bin/bash

# 单元测试
source "${VENV_DIR}/bin/activate"
WORKSPACE="./dbm-ui"

cd $WORKSPACE || exit

FAILED_COUNT=0
celery beat -A config.prod -l info --pidfile="/tmp/celerybeat.pid"
ps -ef | pgrep "celery beat"
if [[ $? -ne 0 ]];
then
  echo "Error: start celery beat error"
  FAILED_COUNT=$[$FAILED_COUNT+1]
fi

celery worker -A config.prod -l info -c 1
ps -ef | pgrep "celery worker"
if [[ $? -ne 0 ]];
then
  echo "Error: python manage.py migrate 执行失败！请检查 migrations 文件"
  cat /tmp/migrate.log
  FAILED_COUNT=$[$FAILED_COUNT+1]
fi

if [[ $TEST_NOT_SUCCESS_COUNT -ne 0 ]];
then
  echo "${TEST_LOGS}"
  exit 1
fi

exit 0
