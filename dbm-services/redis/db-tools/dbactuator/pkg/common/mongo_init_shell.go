package common

// MongoShellInit TODO
var MongoShellInit = `#!/bin/sh
# 新建用户

function _exit() {
        rm $0
        exit
}
#handler nscd restart  默认使用mysql用户
#如果存在mysql用户组就groupadd mysql -g 202
egrep "^{{group}}" /etc/group >& /dev/null
if [ $? -ne 0 ]
then
groupadd {{group}} -g 2000
fi
#考虑到可能上架已运行的机器，userdel有风险，不采用这种方法
#如果存在user用户就删掉（因为有可能1）id不为30019，2）不存在home目录）
id {{user}} >& /dev/null
if [ $? -ne 0 ]
then
        useradd -m -d /home/{{user}} -g 2000 -G users -u 2000 {{user}}
        chage -M 99999 {{user}}
        if [ ! -d /home/{{user}} ];
        then
                mkdir -p /home/{{user}}
        fi
        chmod 755 /home/{{user}}
        usermod -d /home/{{user}} {{user}} 2>/dev/null
fi
if [[ -z "$MONGO_DATA_DIR" ]]
then
   echo "env MONGO_DATA_DIR cannot be empty" >&2
   exit -1
fi
if [[ -z "$MONGO_BACKUP_DIR" ]]
then
   echo "env MONGO_BACKUP_DIR cannot be empty" >&2
   exit -1
fi

if [ ! -d $MONGO_DATA_DIR ]
then
        mkdir -p $MONGO_DATA_DIR
fi

if [ ! -d $MONGO_BACKUP_DIR ]
then
        mkdir -p $RMONGO_BACKUP_DIR
fi

#添加mongo安装锁文件
if [ ! -f $MONGO_DATA_DIR/mongoinstall.lock ]
then
        touch $MONGO_DATA_DIR/mongoinstall.lock
fi

#如果存在mysql用户,上面那一步会报错，也不会创建/home/mysql，所以判断下并创建/home/mysql
if [ ! -d /data ];
then
	ln -s $MONGO_BACKUP_DIR /data
fi
if [ ! -d /data1 ];
then
	ln -s $MONGO_DATA_DIR /data1
fi
if [[ ! -d /data1/dbha ]]
then
        mkdir -p /data1/dbha
fi
chown -R {{user}} /data1/dbha
if [[ ! -d /data/dbha ]]
then
        mkdir -p /data/dbha
fi
chown -R {{user}} /data/dbha
if [[ ! -d /data/install ]]
then
        mkdir -p /data/install
        chown -R {{user}} /data/install
fi
if [[ ! -d $MONGO_BACKUP_DIR/dbbak ]]
then
        mkdir -p $MONGO_BACKUP_DIR/dbbak
        chown -R {{user}} $MONGO_BACKUP_DIR/dbbak
fi
chown -R {{user}} /home/{{user}}
chmod -R a+rwx /data/install
rm -rf /home/{{user}}/install
ln -s /data/install /home/{{user}}/install
chown -R {{user}} /home/{{user}}/install
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
FOUND=$(grep 'export PATH=/usr/local/mongodb/bin/:$PATH' /etc/profile)
if [ -z "$FOUND" ]; then
        echo 'export PATH=/usr/local/mongodb/bin/:$PATH' >> /etc/profile
fi
FOUND_umask=$(grep '^umask 022' /etc/profile)
if [ -z "$FOUND_umask" ]; then
        echo 'umask 022' >> /etc/profile
fi
FOUND=$(grep 'vm.swappiness = 0' /etc/sysctl.conf)
if [ -z "$FOUND" ];then
echo "vm.swappiness = 0" >> /etc/sysctl.conf
fi
FOUND=$(grep 'kernel.pid_max = 200000' /etc/sysctl.conf)
if [ -z "$FOUND" ];then
echo "kernel.pid_max = 200000" >> /etc/sysctl.conf
fi

FOUND=$(grep '{{user}} soft nproc 64000' /etc/security/limits.conf)
if [ -z "$FOUND" ];then
echo "{{user}} soft nproc 64000" >> /etc/security/limits.conf
fi
FOUND=$(grep '{{user}} hard nproc 64000' /etc/security/limits.conf)
if [ -z "$FOUND" ];then
echo "{{user}} hard nproc 64000" >> /etc/security/limits.conf
fi
FOUND=$(grep '{{user}} soft fsize unlimited' /etc/security/limits.conf)
if [ -z "$FOUND" ];then
echo "{{user}} soft fsize unlimited" >> /etc/security/limits.conf
fi
FOUND=$(grep '{{user}} hard fsize unlimited' /etc/security/limits.conf)
if [ -z "$FOUND" ];then
echo "{{user}} hard fsize unlimited" >> /etc/security/limits.conf
fi
FOUND=$(grep '{{user}} soft memlock unlimited' /etc/security/limits.conf)
if [ -z "$FOUND" ];then
echo "{{user}} soft memlock unlimited" >> /etc/security/limits.conf
fi
FOUND=$(grep '{{user}} hard memlock unlimited' /etc/security/limits.conf)
if [ -z "$FOUND" ];then
echo "{{user}} hard memlock unlimited" >> /etc/security/limits.conf
fi
FOUND=$(grep '{{user}} soft as unlimited' /etc/security/limits.conf)
if [ -z "$FOUND" ];then
echo "{{user}} soft as unlimited" >> /etc/security/limits.conf
fi
FOUND=$(grep '{{user}} hard as unlimited' /etc/security/limits.conf)
if [ -z "$FOUND" ];then
echo "{{user}} hard as unlimited" >> /etc/security/limits.conf
fi

FOUND=$(grep 'session required pam_limits.so' /etc/pam.d/login)
if [ -z "$FOUND" ];then
echo "session required pam_limits.so" >> /etc/pam.d/login
fi

FOUND=$(grep 'session required pam_limits.so' /etc/pam.d/su)
if [ -z "$FOUND" ];then
echo "session required pam_limits.so" >> /etc/pam.d/su
fi

/sbin/sysctl -p
_exit`
