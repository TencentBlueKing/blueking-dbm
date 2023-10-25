#!/usr/bin/env sh

#检查必要文件是否存在
confFile="./config.yaml"
dtsBinFile="./redis_dts_server"
tredisdumpBinFile="./tredisdump"
redisCliBinFile="./redis-cli"
syncTemplateConfFile="./tendisssd-sync-template.conf"
scpFile="./scp.exp.2"
if [[ ! -e "$confFile" ]]
then
	echo "error:$confFile not exists"
	exit -1
fi

if [[ ! -e "$dtsBinFile" ]]
then
	echo "error:$dtsBinFile not exists"
	exit -1
fi

if [[ ! -e "$tredisdumpBinFile" ]]
then
	echo "error:$tredisdumpBinFile not exists"
	exit -1
fi

if [[ ! -e "$redisCliBinFile" ]]
then
	echo "error:$redisCliBinFile not exists"
	exit -1
fi

if [[ ! -e "$syncTemplateConfFile" ]]
then
	echo "error:$syncTemplateConfFile not exists"
	exit -1
fi

if [[ ! -e "$scpFile" ]]
then
	echo "error:$scpFile not exists"
	exit -1
fi

# 如果已经有一个 redis_dts_server 在运行,不能直接启动
processCnt=$(ps -ef|grep $dtsBinFile|grep -v grep|grep -v sync|wc -l)
if [[ $processCnt -ge 1 ]]
then
	echo "error:there are a 'redis_dts_server' running"
	ps -ef|grep $dtsBinFile|grep -v grep|grep -v sync
	exit -1
fi

# 启动 redis_dts_server
chmod u+x $dtsBinFile
nohup $dtsBinFile &

sleep 2

#再次检查是否启动成功
processCnt=$(ps -ef|grep $dtsBinFile|grep -v grep|grep -v sync|wc -l)
if [[ $processCnt -ge 1 ]]
then
	echo "success:start $dtsBinFile success"
else
	echo "error: start $dtsBinFile fail"
	exit -1
fi