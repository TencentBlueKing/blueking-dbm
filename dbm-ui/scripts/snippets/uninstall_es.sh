#!/bin/bash

su - mysql -c "supervisorctl stop all"
su - mysql -c "crontab -r"
rm -rf /data/es* /data1/es* /data2/es* /data3/es* /data4/es*
rm /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord
rm /usr/bin/java
ps -ef | grep supervisord | grep -v grep | awk {'print "kill -9 " $2'} | sh
ps -ef | grep telegraf | grep -v grep | awk {'print "kill -9 " $2'} | sh
ps -ef | grep x-pack-ml | grep -v grep | awk {'print "kill -9 " $2'} | sh
df |grep data|grep -vw '/data'|awk '{print $NF}'|while read line;do rm  -rf $line/esdata*;done
sed -i '/esprofile/d' /etc/profile