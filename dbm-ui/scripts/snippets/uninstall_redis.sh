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
rm -rf /usr/local/twemproxy*
rm -rf /usr/local/redis*
rm -rf /usr/local/tendisplus-*
