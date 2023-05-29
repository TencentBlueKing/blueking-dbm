#!/bin/bash

sed -i -e 's/net.ipv4.tcp_tw_recycle=1/net.ipv4.tcp_tw_recycle=0/g' /etc/sysctl.conf
ps -ef | grep mysql | grep -v grep | awk '{print $2}' | xargs kill -9
rm -rf /data/install
rm -rf /data/redis
rm -rf /data/twemproxy*
rm -rf /data/predix*
rm -rf /data1/install
rm -rf /data1/redis
rm -rf /data1/twemproxy*
rm -rf /data1/predix*
rm -rf /usr/local/twemproxy*
rm -rf /usr/local/predix*
rm -rf /usr/local/redis*
rm -rf /usr/local/tendisplus-*
rm -rf /home/mysql/bk-dbmon
rm -rf /data/dbbak
rm /data1

sed -i '/net.ipv4.ip_local_port_range/d' /etc/sysctl.conf
sed -i '/net.ipv4.tcp_tw_reuse/d' /etc/sysctl.conf
sed -i '/net.ipv4.tcp_tw_recycle/d' /etc/sysctl.conf
