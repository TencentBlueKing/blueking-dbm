#!/usr/bin/env sh

DIR=$(dirname $0)
cd $DIR

nowtime=$(date "+%Y-%m-%d %H:%M:%S")
confFile="dbmon-config.yaml"

httpAddr=$(grep 'http_address' dbmon-config.yaml |awk '{print $2}'|sed -e "s/^'//" -e "s/'$//" -e 's/^"//' -e 's/$"//')
httpAddr="http://$httpAddr/health"

if curl $httpAddr >/dev/null 2>&1
then
    ps aux|grep 'bk-dbmon --config'|grep -v grep|awk '{print $2}'|xargs kill
else
    echo "[$nowtime] bk-dbmon not running"
    exit 0
fi

if curl $httpAddr >/dev/null 2>&1
then
    echo "[$nowtime] bk-dbmon kill fail,still running"
    exit 0
else
    echo "[$nowtime] bk-dbmon stop success"
fi

delete_cron () {
        P=`pwd`
        CMD="cd $P && sh start.sh >> start.log 2>&1"
        TMPF=./crontab.old

        if crontab -l 2>/dev/null | grep -P "bk-dbmon.*start.sh" 1>/dev/null ;then
                echo "[$nowtime] delete_from_cron";
                crontab -l 2>/dev/null | grep -v "bk-dbmon.*start.sh" | grep -v "^#.*bk-dbmon start.sh" > $TMPF
                crontab $TMPF
        fi
}

delete_cron