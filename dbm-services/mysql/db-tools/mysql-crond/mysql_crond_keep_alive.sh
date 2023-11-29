#!/bin/sh

function print_log() {
        NOW=$(date +"%Y-%m-%d %H:%M:%S")
        echo "$NOW $@"
}

function mysql_crond_is_alive() {
        for i in {1..5}
        do
                PID=$(pgrep -x 'mysql-crond' 2>/dev/null)
                if [ $? -eq 0 ];then
                        print_log "mysql-crond process found, pid=${PID}"
                        curl -XGET http://127.0.0.1:9999/entries 1>/dev/null 2>&1
                        if [ $? -eq 0 ];then
                                print_log "connect mysql-crond success"
                                return 0
                        else
                                print_log "connect mysql-crond failed, kill pid=${PID}"
                                kill -9 $PID
                        fi
                else
                        print_log "mysql-crond process not found"
                fi

                sleep 1
        done
        return 1
}

mysql_crond_is_alive
if [ $? -ne 0 ];then
        print_log "mysql-crond not alive, try to start"
        cd /home/mysql/mysql-crond
        nohup ./start.sh -c runtime.yaml &
else
        print_log "mysql-crond alive"
fi