#!/bin/bash

su - mysql -c "supervisorctl stop all"
su - mysql -c "crontab -r"
rm -rf /data/influxdb* /data1/influxdb*
rm /etc/supervisord.conf /usr/local/bin/supervisorctl /usr/local/bin/supervisord
rm /usr/bin/java
ps -ef | grep supervisord | grep -v grep | awk {'print "kill -9 " $2'} | sh
