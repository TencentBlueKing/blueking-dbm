#!/bin/sh
# 新建mysql.mysql用户
##
# mysql scripts
##
function _exit() {
        rm $0
        exit
}
#handler nscd restart
#如果存在mysql用户组就groupadd mysql -g 202
egrep "^mysql" /etc/group >&/dev/null
if [ $? -ne 0 ]; then
        groupadd mysql -g 202
fi
#考虑到可能上架已运行的机器，userdel有风险，不采用这种方法
#如果存在mysql用户就删掉（因为有可能1）id不为30019，2）不存在home目录）
id mysql >&/dev/null
if [ $? -ne 0 ]; then
        useradd -m -d /home/mysql -g 202 -G users -u 30019 mysql
        chage -M 99999 mysql
        if [ ! -d /home/mysql ]; then
                mkdir -p /home/mysql
        fi
        chmod 755 /home/mysql
        usermod -d /home/mysql mysql 2>/dev/null
fi

if [ -L "/data1" ] && [ ! -e "/data1" ]
then
  echo "/data1 is an invalid soft link. Removing it..."
  rm "/data1"
fi

if [ -L "/data" ] && [ ! -e "/data" ]
then
  echo "/data is an invalid soft link. Removing it..."
  rm "/data"
fi

if [[ -z "$REDIS_DATA_DIR" ]]; then
        echo "env REDIS_DATA_DIR cannot be empty" >&2
        exit -1
fi
if [[ -z "$REDIS_BACKUP_DIR" ]]; then
        echo "env REDIS_BACKUP_DIR cannot be empty" >&2
        exit -1
fi

if [ ! -d $REDIS_DATA_DIR ]; then
        mkdir -p $REDIS_DATA_DIR
fi

if [ ! -d $REDIS_BACKUP_DIR ]; then
        mkdir -p $REDIS_BACKUP_DIR
fi

#如果存在mysql用户,上面那一步会报错，也不会创建/home/mysql，所以判断下并创建/home/mysql
if [ ! -d /data ]; then
        ln -s $REDIS_BACKUP_DIR /data
fi
if [ ! -d /data1 ]; then
        ln -s $REDIS_DATA_DIR /data1
fi
if [[ ! -d /data1/dbha ]]; then
        mkdir -p /data1/dbha
fi
chown -R mysql /data1/dbha
if [[ ! -d /data/dbha ]]; then
        mkdir -p /data/dbha
fi
chown -R mysql /data/dbha
if [[ ! -d /data/install ]]; then
        mkdir -p /data/install
        chown -R mysql /data/install
fi
if [[ ! -d $REDIS_BACKUP_DIR/dbbak ]]; then
        mkdir -p $REDIS_BACKUP_DIR/dbbak
        chown -R mysql $REDIS_BACKUP_DIR/dbbak
fi
chown -R mysql /home/mysql
chmod -R a+rwx /data/install
rm -rf /home/mysql/install
ln -s /data/install /home/mysql/install
chown -R mysql /home/mysql/install
password="$2"
#password=$(echo "$2" | /home/mysql/install/lib/tools/base64 -d)
echo "mysql:$password" | chpasswd
FOUND=$(grep -A 2 -B 2 'ulimit -n 204800' /etc/profile || { true; } )
if [ -z "$FOUND" ]; then
cat >> /etc/profile <<EOF
if [ "\`id -u\`" == "0" ] ;then
:
ulimit -n 204800
fi
EOF
elif [[ $FOUND =~ "id -u" ]]; then
echo "ok"
else
# 删除 ulimit -n 204800,重新插入
sed -i '/ulimit -n 204800/d' /etc/profile
cat >> /etc/profile <<EOF
if [ "\`id -u\`" == "0" ] ;then
:
ulimit -n 204800
fi
EOF
fi

FOUND=$(grep 'export LC_ALL=en_US' /etc/profile)
if [ -z "$FOUND" ]; then
        echo 'export LC_ALL=en_US' >>/etc/profile
fi
FOUND=$(grep 'export PATH=/usr/local/mysql/bin/:$PATH' /etc/profile)
if [ -z "$FOUND" ]; then
        echo 'export PATH=/usr/local/mysql/bin/:$PATH' >>/etc/profile
fi
FOUND_umask=$(grep '^umask 022' /etc/profile)
if [ -z "$FOUND_umask" ]; then
        echo 'umask 022' >>/etc/profile
fi
FOUND=$(grep 'fs.aio-max-nr' /etc/sysctl.conf)
if [ -z "$FOUND" ]; then
        echo "fs.aio-max-nr=1024000" >>/etc/sysctl.conf
fi
FOUND=$(grep 'vm.overcommit_memory = 1' /etc/sysctl.conf)
if [ -z "$FOUND" ]; then
        echo "vm.overcommit_memory = 1" >>/etc/sysctl.conf
fi
FOUND=$(grep 'vm.swappiness = 0' /etc/sysctl.conf)
if [ -z "$FOUND" ]; then
        echo "vm.swappiness = 0" >>/etc/sysctl.conf
fi
FOUND=$(grep -i 'net.ipv4.ip_local_reserved_ports=30000-31000,40000-41000,50000-52000' /etc/sysctl.conf)
if [ -z "$FOUND" ]; then
        echo "net.ipv4.ip_local_reserved_ports=30000-31000,40000-41000,50000-52000" >>/etc/sysctl.conf
fi
# 生成 core 文件相关配置
if [[ ! -d /data/corefile ]]; then
        mkdir -p /data/corefile
        chmod  777 /data/corefile
fi
FOUND=$(grep -i 'soft core unlimited' /etc/security/limits.conf)
if [ -z "$FOUND" ]; then
        echo "* soft core unlimited" >>/etc/security/limits.conf
fi
FOUND=$(grep -i 'soft hard unlimited' /etc/security/limits.conf)
if [ -z "$FOUND" ]; then
        echo "* soft hard unlimited" >>/etc/security/limits.conf
fi
FOUND=$(grep -i 'kernel.core_uses_pid = 0' /etc/sysctl.conf)
if [ -z "$FOUND" ]; then
        echo "kernel.core_uses_pid = 0" >>/etc/sysctl.conf
fi
FOUND=$(grep -i 'kernel.core_pattern= /data/corefile/core_%e_%t' /etc/sysctl.conf)
if [ -z "$FOUND" ]; then
        echo "kernel.core_pattern= /data/corefile/core_%e_%t" >>/etc/sysctl.conf
fi

/sbin/sysctl -p
_exit
