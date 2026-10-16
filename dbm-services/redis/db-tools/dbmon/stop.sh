#!/usr/bin/env sh

source /etc/profile
source ~/.bash_profile

DIR=$(dirname $0)
cd $DIR

nowtime=$(date "+%Y-%m-%d %H:%M:%S")
confFile="dbmon-config.yaml"

# 清理keylifecycle离线分析遗留的临时keys文件(v.*.keys)
# 进程被kill时,go代码里的defer清理逻辑不会执行,停止时由此兜底
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

httpAddr=$(grep 'http_address' dbmon-config.yaml | awk '{print $2}' | sed -e "s/^'//" -e "s/'$//" -e 's/^"//' -e 's/$"//')
httpAddr="http://$httpAddr/health"

if curl $httpAddr >/dev/null 2>&1; then
    ps aux | grep 'bk-dbmon --config' | grep -v grep | awk '{print $2}' | xargs kill
else
    echo "[$nowtime] bk-dbmon not running"
fi

if curl $httpAddr >/dev/null 2>&1; then
    echo "[$nowtime] bk-dbmon kill fail,still running"
    exit 0
else
    echo "[$nowtime] bk-dbmon stop success"
    # 确认进程已停止,清理遗留的临时keys文件
    clean_stale_keys_files
fi

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

delete_cron
