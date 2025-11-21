#!/bin/bash

# ./start.sh
# ./start.sh -c runtime.yaml

killall mysql-monitor

pgrep -x 'mysql-crond' && echo "mysql-crond process already running" && exit 1

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
if [ $# -eq 0 ];then
  # echo "run default ./mysql-crond -c runtime.yaml" 
  START_CMD="cd $SCRIPT_DIR && nohup ./mysql-crond -c runtime.yaml 1>/dev/null 2>start-crond.err &"
else
  START_CMD="cd $SCRIPT_DIR && nohup ./mysql-crond ${@:1} 1>/dev/null 2>start-crond.err &"
fi



if [ $(id -u) -eq 0 ];then
  cd $SCRIPT_DIR && > start-crond.err && > mysql-crond.pid && chown mysql start-crond.err && chown mysql mysql-crond.pid
  su - mysql -c "$START_CMD"
else
  cd $SCRIPT_DIR && > start-crond.err && > mysql-crond.pid
  $START_CMD
fi

sleep 1
pgrep -x 'mysql-crond' >mysql-crond.pid
if [ $? -gt 0 ];then
  cat start-crond.err
  exit 1
fi