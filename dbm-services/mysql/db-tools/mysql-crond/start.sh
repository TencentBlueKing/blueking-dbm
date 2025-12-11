#!/bin/bash

killall mysql-monitor 2>/dev/null

pgrep -x 'mysql-crond' && echo "mysql-crond process already running" && exit 1

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
if [ $# -eq 0 ];then
  START_CMD="$SCRIPT_DIR/mysql-crond -c $SCRIPT_DIR/runtime.yaml 1>/dev/null 2>start-crond.err"
else
  START_CMD="$SCRIPT_DIR/mysql-crond ${@:1} 1>/dev/null 2>start-crond.err"
fi


if [ $(id -u) -eq 0 ];then
  cd $SCRIPT_DIR && > start-crond.err && > mysql-crond.pid && chown mysql start-crond.err && chown mysql mysql-crond.pid
  setsid su - mysql -c "$START_CMD &"
else
  cd $SCRIPT_DIR && > start-crond.err && > mysql-crond.pid
  setsid sh -c "exec $START_CMD" < /dev/null &
fi

sleep 1
pgrep -x 'mysql-crond' >mysql-crond.pid
if [ $? -gt 0 ];then
  cat start-crond.err
  exit 1
fi