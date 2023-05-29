#!/bin/sh

USERNAME=$(id -u -n)
CRONTAB_OLD=$(mktemp)

if [ "$USERNAME" == "mysql" ];then
        crontab -l | grep -v "mysql_crond_keep_alive" > $CRONTAB_OLD
        crontab $CRONTAB_OLD
elif [ "$USERNAME" == "root" ];then
        crontab -umysql -l | grep -v "mysql_crond_keep_alive" > $CRONTAB_OLD
        crontab -umysql $CRONTAB_OLD
else
        echo "can't run as $USERNAME"
        exit 1
fi