#!/bin/bash

anynowtime="date +'%Y-%m-%d %H:%M:%S'"
NOW="echo [\`$anynowtime\`][PID:$$]"

##### 可在脚本开始运行时调用，打印当时的时间戳及PID。
function job_start
{
    echo "`eval $NOW` job_start"
}

##### 可在脚本执行成功的逻辑分支处调用，打印当时的时间戳及PID。 
function job_success
{
    MSG="$*"
    echo "`eval $NOW` job_success:[$MSG]"
    exit 0
}

##### 可在脚本执行失败的逻辑分支处调用，打印当时的时间戳及PID。
function job_fail
{
    MSG="$*"
    echo "`eval $NOW` job_fail:[$MSG]"
    exit 1
}

job_start


#初始化
useradd mysql -g root -s /bin/bash -d /home/mysql
echo  -e "mysql soft memlock unlimited\nmysql hard memlock unlimited" >> /etc/security/limits.conf
echo -e "vm.max_map_count=262144\nvm.swappiness=1" >> /etc/sysctl.conf ;sysctl -p
mkdir -p /data/esenv 
chown -R mysql /data/esenv
mkdir -p /data/eslog 
chown -R mysql /data/eslog

cat << 'EOF' > /data/esenv/esprofile
export JAVA_HOME=/data/esenv/es/jdk
export CLASSPATH=".:$JAVA_HOME/lib:$JRE/lib:$CLASSPATH"
export ES_HOME=/data/esenv/es
export ES_CONF_DIR=$ES_HOME/config
export PATH=${JAVA_HOME}/bin:${ES_HOME}/bin:${ES_HOME}/sbin:$PATH
EOF

chown mysql  /data/esenv/esprofile

sed -i '/esprofile/d' /etc/profile
echo "source /data/esenv/esprofile" >>/etc/profile

job_success "初始化完成"