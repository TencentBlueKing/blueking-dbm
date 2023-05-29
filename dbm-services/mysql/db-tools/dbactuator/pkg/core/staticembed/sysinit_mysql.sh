#!/bin/sh
# 新建mysql.mysql用户
##
# mysql scripts 
##
# depends: ~/abs/ssh.exp  ~/abs/scp.exp
function _exit() {
        rm $0
        exit
}
#chmod o+rx /usr/local/ieod-public/sysinfo  -R
#chmod o+rx /usr/local/agenttools/agent
#chmod o+rx /usr/local/agenttools/agent/agentRep* 
#handler nscd restart
#如果存在mysql用户组就groupadd mysql -g 202
egrep "^mysql" /etc/group >& /dev/null
if [ $? -ne 0 ]
then
groupadd mysql -g 202
fi
#考虑到可能上架已运行的机器，userdel有风险，不采用这种方法
#如果存在mysql用户就删掉（因为有可能1）id不为30019，2）不存在home目录）
id mysql >& /dev/null
if [ $? -ne 0 ]
then
        useradd -m -d /home/mysql -g 202 -G users -u 30019 mysql
        chage -M 99999 mysql
        if [ ! -d /home/mysql ]; 
        then
                mkdir -p /home/mysql
        fi
        chmod 755 /home/mysql
        usermod -d /home/mysql mysql
fi
#如果存在mysql用户,上面那一步会报错，也不会创建/home/mysql，所以判断下并创建/home/mysql
if [ ! -d /data ];
then
	mkdir -p /data1/data/
	ln -s /data1/data/ /data
fi
if [ ! -d /data1 ];
then
	mkdir -p /data/data1/
	ln -s /data/data1 /data1
fi
mkdir -p /data1/dbha
chown -R mysql /data1/dbha
mkdir -p /data/dbha
chown -R mysql /data/dbha
#mkdir -p /home/mysql/install
#chown -R mysql /home/mysql
#chmod -R a+rwx /home/mysql/install
mkdir -p /data/install
chown -R mysql /home/mysql
chown -R mysql /data/install
chmod -R a+rwx /data/install
rm -rf /home/mysql/install
ln -s /data/install /home/mysql/install
chown -R mysql /home/mysql/install
password="$2"
#password=$(echo "$2" | /home/mysql/install/lib/tools/base64 -d)
echo "mysql:$password" | chpasswd
FOUND=$(grep 'ulimit -n 204800' /etc/profile)
if [ -z "$FOUND" ]; then
        echo 'ulimit -n 204800' >> /etc/profile
fi
FOUND=$(grep 'export LC_ALL=en_US' /etc/profile)
if [ -z "$FOUND" ]; then
        echo 'export LC_ALL=en_US' >> /etc/profile
fi
FOUND=$(grep 'export PATH=/usr/local/mysql/bin/:$PATH' /etc/profile)
if [ -z "$FOUND" ]; then
        echo 'export PATH=/usr/local/mysql/bin/:$PATH' >> /etc/profile
fi
FOUND_umask=$(grep '^umask 022' /etc/profile)
if [ -z "$FOUND_umask" ]; then
        echo 'umask 022' >> /etc/profile
fi
FOUND=$(grep 'fs.aio-max-nr' /etc/sysctl.conf)
if [ -z "$FOUND" ];then
echo "fs.aio-max-nr=1024000" >> /etc/sysctl.conf
/sbin/sysctl -p
fi
_exit
