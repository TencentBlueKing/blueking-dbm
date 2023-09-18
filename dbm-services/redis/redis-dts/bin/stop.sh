#!/usr/bin/env sh

processCnt=$(ps -ef|grep scp.exp.2|grep -v grep|wc -l)
if [[ $processCnt -gt 0 ]]
then
	echo "error:fetching backup file,cannot stop ..."
	exit -1
fi

processCnt=$(ps -ef|grep tredisdump|grep -v grep|wc -l)
if [[ $processCnt -gt 0 ]]
then
	echo "error:tredisdump running,cannot stop ..."
	ps -ef|grep tredisdump|grep -v grep
	exit -1
fi

processCnt=$(ps -ef|grep redis-cli|grep '\-\-pipe'|grep -v grep|wc -l)
if [[ $processCnt -gt 0 ]]
then
	echo "error:importing data running,cannot stop ..."
	ps -ef|grep redis-cli|grep '\-\-pipe'|grep -v grep
	exit -1
fi
processCnt=$(ps -ef|grep redis-dts|grep -v grep|grep -v sync|wc -l)
if [[ $processCnt -eq 0 ]]
then
	echo "success:redis-dts not running"
	exit 0
fi

ps -ef|grep redis-dts|grep -v grep|grep -vi sync|awk '{print $2}'|xargs kill

#再次检查是否stop成功
processCnt=$(ps -ef|grep redis-dts|grep -v grep|grep -v sync|wc -l)
if [[ $processCnt -eq 0 ]]
then
	echo "success:stop redis-dts success"
	exit 0
else
	echo "error: stop redis-dts fail"
	exit -1
fi