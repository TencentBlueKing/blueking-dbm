#!/bin/bash

killall mysql-monitor 2>/dev/null

pgrep -x 'mysql-crond' && echo "mysql-crond process already running" && exit 1

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
START_ERR="$SCRIPT_DIR/start-crond.err"
PID_FILE="$SCRIPT_DIR/mysql-crond.pid"
if [ $# -eq 0 ];then
  START_CMD="$SCRIPT_DIR/mysql-crond -c $SCRIPT_DIR/runtime.yaml 1>/dev/null 2>$START_ERR"
else
  START_CMD="$SCRIPT_DIR/mysql-crond ${@:1} 1>/dev/null 2>$START_ERR"
fi


if [ $(id -u) -eq 0 ];then
  cd $SCRIPT_DIR && > $START_ERR && > $PID_FILE && chown mysql $START_ERR && chown mysql $PID_FILE
  setsid su - mysql -c "$START_CMD &"
else
  cd $SCRIPT_DIR && > $START_ERR && > $PID_FILE
  setsid sh -c "exec $START_CMD" < /dev/null &
fi

sleep 1
pgrep -x 'mysql-crond' >$PID_FILE
if [ $? -gt 0 ];then
  cat $START_ERR >&2
  exit 1
fi