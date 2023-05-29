#!/bin/bash

ps -ef | grep mysql | grep -v grep | awk '{print $2}' | xargs kill -9
rm -rf /data/install
rm -rf /data/redis
rm -rf /data/twemproxy*
rm -rf /data/predix*

rm -rf /data1/install
rm -rf /data1/redis
rm -rf /data1/twemproxy*
rm -rf /data1/predix*

rm -rf /data/mysqldata/
rm -rf /data/mysql-proxy/
rm -rf /data/mysqllog/

rm -rf /data1/mysqldata/
rm -rf /data1/mysql-proxy/
rm -rf /data1/mysqllog/

rm -rf /usr/local/twemproxy*
rm -rf /usr/local/predix*
rm -rf /usr/local/redis*
rm -rf /usr/local/tendisplus-*

rm -rf /home/mysql/mysql-crond*
rm -rf /home/mysql/dbareport

sed -i 's/^ulimit/#&/g' /etc/profile
sed -i "s/^[^#].*esprofile/#&/g" /etc/profile
sed -i "s/^[^#].*hdfsProfile/#&/g" /etc/profile

rm -rf /data/data1
rm -rf /data/dbbak
rm -rf /data/dbha
rm -rf /data/es*
rm -rf /data/kafka*
rm -rf /data/mysql*
rm -rf /data/zklog
rm -rf /usr/local/gse2_bkte
rm -rf /usr/local/mysql*

rm -rf /usr/local/gse_cloud/external_plugins/sub_9250_service_2000027056/mysql_exporter_test1/mysql_exporter_test1
rm -rf /usr/local/gse_cloud/external_plugins/sub_9250_service_2000027058/mysql_exporter_test1/mysql_exporter_test1

rm -rf /home/mysql/mysql-crond/mysql-crond
rm -rf /usr/local/gse_cloud/agent/bin/gse_agent
rm -rf /usr/local/gse_cloud/plugins/bin/bkmonitorbeat
rm -rf /usr/local/gse_cloud/plugins/bin/bkunifylogbeat

ps aux|grep mysql-crond|xargs -i  kill  {};

sed -i '/mysql*/d'  /var/spool/cron/*
