#!/bin/bash

echo "
* - nofile 200000
* soft nofile 200000
* hard nofile 200000
" >> /etc/security/limits.conf


echo never >> /sys/kernel/mm/transparent_hugepage/enabled && echo never >>  /sys/kernel/mm/transparent_hugepage/defrag
echo "
never >> /sys/kernel/mm/transparent_hugepage/enabled
never >> /sys/kernel/mm/transparent_hugepage/defrag
" >> /etc/rc.local

# 设置vm.overcommit_memory 为1 设置vm.swappiness 为1

echo "
vm.overcommit_memory=1
vm.swappiness=1
net.ipv4.ip_local_port_range=25000 50000
" >> /etc/sysctl.conf

id hadoop >& /dev/null
if [ $? -ne 0 ]
then
   useradd hadoop -g root -s /bin/bash -d /home/hadoop
fi

mkdir -p /data/hadoopenv
chown -R hadoop.root /data/hadoopenv
mkdir -p /data/hadoopdata
chown -R hadoop.root /data/hadoopdata


cat << 'EOF' > /data/hadoopenv/hdfsProfile
export JAVA_HOME="/data/hadoopenv/java"
export CLASSPATH=".:$JAVA_HOME/lib:$JRE/lib:$CLASSPATH"
export HADOOP_HOME="/data/hadoopenv/hadoop"
export HADOOP_CONF_DIR="$HADOOP_HOME/etc/hadoop"
export PATH="${JAVA_HOME}/bin:${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin:$PATH"
EOF

chown hadoop:root /data/hadoopenv/hdfsProfile

sed -i '/hdfsProfile/d' /etc/profile
echo "source /data/hadoopenv/hdfsProfile" >>/etc/profile
