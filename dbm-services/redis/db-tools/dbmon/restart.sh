#!/usr/bin/env sh

source /etc/profile
source ~/.bash_profile

DIR=$(dirname $0)
cd $DIR

nowtime=$(date "+%Y-%m-%d %H:%M:%S")
confFile="dbmon-config.yaml"

# 清理keylifecycle离线分析遗留的临时keys文件(v.*.keys)
# 进程被kill时,go代码里的defer清理逻辑不会执行,重启时由此兜底
clean_stale_keys_files() {
    statDir=$(grep 'stat_dir' dbmon-config.yaml 2>/dev/null | awk '{print $2}' | sed -e "s/^'//" -e "s/'$//" -e 's/^"//' -e 's/"$//')
    if [[ -z "$statDir" ]]; then
        statDir="/data/dbbak/keylifecycle"
    fi
    if [[ -d "$statDir" ]]; then
        rm -f $statDir/v.*.keys 2>/dev/null
        echo "[$nowtime] clean stale keys files in $statDir"
    fi
}

add_to_cron() {
    P=$(pwd)
    CMD="cd $P && sh start.sh >> ./logs/start.log 2>&1"
    TMPF=./crontab.old

    # Maybe 'crontab -l' will output 'no crontab for xxx',so we output to 2>/dev/null
    if crontab -l 2>/dev/null | grep "$CMD" 1>/dev/null; then
        :
    else
        crontab -l 2>/dev/null >$TMPF
        cat >>$TMPF <<EOF
# bk-dbmon start.sh , check and start every 1 min #`date "+%F %T"`
* *  * * * $CMD
EOF
        crontab $TMPF
        echo "[$nowtime] add to cron"
    fi
}

add_to_cron

httpAddr=$(grep 'http_address' dbmon-config.yaml | awk '{print $2}' | sed -e "s/^'//" -e "s/'$//" -e 's/^"//' -e 's/$"//')
httpAddr="http://$httpAddr/health"

if curl $httpAddr >/dev/null 2>&1; then
    echo "[$nowtime] bk-dbmon is running, try restart. "
    ps aux | grep 'bk-dbmon --config' | grep -v grep | awk '{print $2}' | xargs kill
    # 等待旧进程退出,确认停止后清理遗留的临时keys文件(清理失败不阻塞重启)
    sleep 1
    if ! curl $httpAddr >/dev/null 2>&1; then
        clean_stale_keys_files
    else
        echo "[$nowtime] old bk-dbmon still running, skip clean stale keys files"
    fi
fi

if [[ ! -e $confFile ]]; then
    echo "[$nowtime] $confFile not exists"
    exit -1
fi

if [[ ! -d "./logs" ]]; then
    mkdir -p ./logs
fi

nohup ./bk-dbmon --config=$confFile >>./logs/start.log 2>&1 &

sleep 1

if curl $httpAddr >/dev/null 2>&1; then
    echo "[$nowtime] bk-dbmon start success"
else
    echo "[$nowtime] bk-dbmon start fail,bk-dbmon not running"
    exit -1
fi

sleep 2
ps -ef|grep dbmon|grep -v grep ;crontab -l|grep dbmon
