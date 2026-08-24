#!/bin/bash
# 当 db-event-consumer 进程存在时，每隔 10s 采集一次 heap profile

while true; do
    if pgrep -f "db-event-consumer" > /dev/null 2>&1; then
        filename="$(date '+%Y%m%d_%H%M%S')_heap.out"
        curl -s -o "${filename}" "http://127.0.0.1:8003/debug/pprof/heap"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 已采集 heap profile: ${filename}"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] db-event-consumer 进程不存在，退出"
        break
    fi
    sleep 10
done
