#!/bin/bash

su - mysql -c "supervisorctl stop all"
su - mysql -c "crontab -r"
rm -rf /data/pulsar* /data1/pulsar* /data2/pulsar* /data3/pulsar* /data4/pulsar*
rm /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord
rm /usr/bin/java
ps -ef | grep supervisord | grep -v grep | awk {'print "kill -9 " $2'} | sh

df |grep data|grep -vw '/data'|awk '{print $NF}'|while read line;do rm  -rf $line/pulsardata*;done
sed -i '/pulsarprofile/d' /etc/profile