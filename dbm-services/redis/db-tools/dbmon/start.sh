#!/usr/bin/env sh

DIR=$(dirname $0)
cd $DIR

nowtime=$(date "+%Y-%m-%d %H:%M:%S")
confFile="dbmon-config.yaml"

httpAddr=$(grep 'http_address' dbmon-config.yaml |awk '{print $2}'|sed -e "s/^'//" -e "s/'$//" -e 's/^"//' -e 's/$"//')
httpAddr="http://$httpAddr/health"

if curl $httpAddr >/dev/null 2>&1
then
    echo "[$nowtime] bk-dbmon is running"
    exit 0
fi

if [[ ! -e $confFile ]]
then
    echo "[$nowtime] $confFile not exists"
    exit -1
fi

if [[ ! -d "./logs" ]]
then
    mkdir -p ./logs
fi

nohup ./bk-dbmon --config=$confFile >>./logs/start.log 2>&1 &

sleep 1

if curl $httpAddr >/dev/null 2>&1
then
    echo "[$nowtime] bk-dbmon start success"
else
    echo "[$nowtime] bk-dbmon start fail,bk-dbmon not running"
    exit -1
fi

add_to_cron () {
        P=`pwd`
        CMD="cd $P && sh start.sh >> start.log 2>&1"
        TMPF=./crontab.old

        # Maybe 'crontab -l' will output 'no crontab for xxx',so we output to 2>/dev/null
        if crontab -l 2>/dev/null | grep "$CMD" 1>/dev/null ;then
		:
        else
                crontab -l 2>/dev/null > $TMPF
                cat >> $TMPF <<EOF
# bk-dbmon start.sh , check and start every 2 min
*/2 *  * * * $CMD
EOF
                crontab $TMPF
		echo "[$nowtime] add to cron"
        fi
}

add_to_cron
