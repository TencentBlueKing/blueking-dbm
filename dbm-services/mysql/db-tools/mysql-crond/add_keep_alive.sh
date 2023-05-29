#!/bin/sh

USERNAME=$(id -u -n)
CRONTAB_OLD=$(mktemp)

if [ "$USERNAME" == "mysql" ];then
        crontab -l | grep -v "mysql_crond_keep_alive" > $CRONTAB_OLD
elif [ "$USERNAME" == "root" ];then
        crontab -umysql -l | grep -v "mysql_crond_keep_alive" > $CRONTAB_OLD
else
        echo "can't run as $USERNAME"
        exit 1
fi

echo "#DONT EDIT THIS LINE mysql_crond_keep_alive added by $USERNAME at $(date)" >> $CRONTAB_OLD
echo "* * * * * /bin/sh /home/mysql/mysql-crond/mysql_crond_keep_alive.sh >> /home/mysql/mysql-crond/keep_alive.log" >> $CRONTAB_OLD

if [ "$USERNAME" == "mysql" ];then
        crontab $CRONTAB_OLD
elif [ "$USERNAME" == "root" ];then
        crontab -umysql $CRONTAB_OLD
fi