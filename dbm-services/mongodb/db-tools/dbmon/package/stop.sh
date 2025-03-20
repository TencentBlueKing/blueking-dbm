#!/usr/bin/env sh

DIR=$(dirname $0)
cd $DIR

delete_cron() {
    P=$(pwd)
    CMD="cd $P && sh start.sh >> start.log 2>&1"
    TMPF=./crontab.old

    if crontab -l 2>/dev/null | grep -P "bk-dbmon.*start.sh" 1>/dev/null; then
        echo "[$nowtime] delete_from_cron"
        crontab -l 2>/dev/null | grep -v "bk-dbmon.*start.sh" | grep -v "^#.*bk-dbmon start.sh" >$TMPF
        crontab $TMPF
    fi
}




nowtime=$(date "+%Y-%m-%d %H:%M:%S")

confFile="dbmon-config.yaml"

httpAddr=$(./gojq -r --yaml-input  '.http_address' $confFile)
healthUrl="http://$httpAddr/health"
stopUrl="http://$httpAddr/stop"
delete_cron


if curl $stopUrl >/dev/null 2>&1; then
  for i in {1..10}; do
    if curl -sS $healthUrl >/dev/null 2>&1; then
      echo "[$nowtime] bk-dbmon still running,wait 1s"
      sleep 1
    else
      break
    fi
  done
  if curl $httpAddr >/dev/null 2>&1; then
    pid=$(ps aux | grep 'bk-dbmon --config' | grep -v grep | awk '{print $2}')
    if [ -n "$pid" ]; then
      echo "[$nowtime] bk-dbmon still running, kill -9 $pid"
      kill -9 $pid
    fi
  fi
else
  echo "[$nowtime] bk-dbmon not running"
  exit 0
fi


if curl $httpAddr >/dev/null 2>&1; then
    echo "[$nowtime] bk-dbmon kill fail,still running"
    exit 0
else
    echo "[$nowtime] bk-dbmon stop success"
fi


