#!/bin/bash

supervisorctl stop haproxy
service haproxy stop

supervisorctl stop telegraf
service telegraf stop

ps -ef | grep namenode | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep journalnode | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep datanode | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep zookeeper | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep zkfc | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep resourcemanager | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep nodemanager | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep supervisor | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep pypy | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep rsyslogd | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep haproxy | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep telegraf | grep -v grep | awk '{print $2}' | xargs kill -s 9
ps -ef | grep -i filebeat | grep -v grep | awk '{print $2}' | xargs kill -s 9

crontab -r

userdel -f hadoop
userdel -f telegraf
userdel -f haproxy

rpm -e libslz-1.1.0-2.el7.x86_64 --nodeps
rpm -e libslz-1.1.0-2.el6.x86_64 --nodeps
rpm -e haproxy-1.8.12-1.el6.x86_64 --nodeps
rpm -e haproxy-1.8.12-1.el7.x86_64 --nodeps

rm -rf /data/hadoopdata
rm -rf /data/hadoopenv
rm -rf /data/install
rm -rf /home/hadoop
rm -rf /var/spool/mail/hadoop
rm -f /tmp/sysinit.sh

sed -i '/hdfsProfile/d' /etc/profile

exit 0