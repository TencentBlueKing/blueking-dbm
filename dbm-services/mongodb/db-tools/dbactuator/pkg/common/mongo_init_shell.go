package common

// MongoShellInit 初始化os的shell脚本
var MongoShellInit = `#!/bin/sh
# 新建用户

log_info() {
        echo "[mongo-os-init][INFO] $1"
}

log_error() {
        echo "[mongo-os-init][ERROR] $1" >&2
}

function _exit() {
        log_info "cleanup tmp init script"
        rm $0
        exit
}
#handler nscd restart  默认使用mysql用户
#如果存在mysql用户组就groupadd mysql -g 202
log_info "check/create group {{group}}"
egrep "^{{group}}" /etc/group >& /dev/null
if [ $? -ne 0 ]
then
groupadd {{group}} -g 2000
log_info "group {{group}} created"
else
log_info "group {{group}} already exists"
fi
#考虑到可能上架已运行的机器，userdel有风险，不采用这种方法
#如果存在user用户就删掉（因为有可能1）id不为30019，2）不存在home目录）
log_info "check/create user {{user}}"
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
        log_info "user {{user}} created and home initialized"
else
        log_info "user {{user}} already exists"
fi
log_info "validate env MONGO_DATA_DIR"
if [[ -z "$MONGO_DATA_DIR" ]]
then
   log_error "env MONGO_DATA_DIR cannot be empty"
   exit -1
fi
log_info "MONGO_DATA_DIR=$MONGO_DATA_DIR"
log_info "validate env MONGO_BACKUP_DIR"
if [[ -z "$MONGO_BACKUP_DIR" ]]
then
   log_error "env MONGO_BACKUP_DIR cannot be empty"
   exit -1
fi
log_info "MONGO_BACKUP_DIR=$MONGO_BACKUP_DIR"

log_info "ensure data dir exists: $MONGO_DATA_DIR"
if [ ! -d $MONGO_DATA_DIR ]
then
        mkdir -p $MONGO_DATA_DIR
fi
log_info "data dir ready: $MONGO_DATA_DIR"

log_info "ensure backup dir exists: $MONGO_BACKUP_DIR"
if [ ! -d $MONGO_BACKUP_DIR ]
then
        mkdir -p $MONGO_BACKUP_DIR
fi
log_info "backup dir ready: $MONGO_BACKUP_DIR"

#添加mongo安装锁文件
log_info "ensure lock file exists: /tmp/mongoinstall.lock"
if [ ! -f /tmp/mongoinstall.lock ]
then
        touch /tmp/mongoinstall.lock
fi
log_info "lock file ready: /tmp/mongoinstall.lock"

#如果存在mysql用户,上面那一步会报错，也不会创建/home/mysql，所以判断下并创建/home/mysql
if [ ! -d /data ];
then
	ln -s $MONGO_BACKUP_DIR /data
fi
log_info "path /data prepared"
if [ ! -d /data1 ];
then
	ln -s $MONGO_DATA_DIR /data1
fi
log_info "path /data1 prepared"
if [[ ! -d /data1/dbha ]]
then
        mkdir -p /data1/dbha
fi
chown -R {{user}} /data1/dbha
log_info "path /data1/dbha prepared and chowned"
if [[ ! -d /data/dbha ]]
then
        mkdir -p /data/dbha
fi
chown -R {{user}} /data/dbha
log_info "path /data/dbha prepared and chowned"
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
log_info "path $MONGO_BACKUP_DIR/dbbak prepared"
chown -R {{user}} /home/{{user}}
chmod -R a+rwx /data/install
rm -rf /home/{{user}}/install
ln -s /data/install /home/{{user}}/install
chown -R {{user}} /home/{{user}}/install
log_info "home/install links and permissions prepared"
#password="$2"
#password=$(echo "$2" | /home/mysql/install/lib/tools/base64 -d)
#echo "mysql:$password" | chpasswd
FOUND=$(grep 'ulimit -n 204800' /etc/profile)
if [ -z "$FOUND" ]; then
        echo 'ulimit -n 204800' >> /etc/profile
fi
log_info "checked profile item: ulimit"
FOUND=$(grep 'export LC_ALL=en_US' /etc/profile)
if [ -z "$FOUND" ]; then
        echo 'export LC_ALL=en_US' >> /etc/profile
fi
log_info "checked profile item: LC_ALL"
#FOUND=$(grep 'export PATH=/usr/local/mongodb/bin/:$PATH' /etc/profile)
#if [ -z "$FOUND" ]; then
#        echo 'export PATH=/usr/local/mongodb/bin/:$PATH' >> /etc/profile
#fi
FOUND_umask=$(grep '^umask 022' /etc/profile)
if [ -z "$FOUND_umask" ]; then
        echo 'umask 022' >> /etc/profile
fi
log_info "checked profile item: umask"

old_swappiness="$(sysctl -n vm.swappiness 2>/dev/null || echo "unknown")"
FOUND=$(grep 'vm.swappiness = 0' /etc/sysctl.conf)
if [ -z "$FOUND" ];then
echo "vm.swappiness = 0" >> /etc/sysctl.conf
log_info "kernel var vm.swappiness config update: before=${old_swappiness}, target=0"
else
log_info "kernel var vm.swappiness config exists: before=${old_swappiness}, target=0"
fi

old_pid_max="$(sysctl -n kernel.pid_max 2>/dev/null || echo "unknown")"
FOUND=$(grep 'kernel.pid_max = 200000' /etc/sysctl.conf)
if [ -z "$FOUND" ];then
echo "kernel.pid_max = 200000" >> /etc/sysctl.conf
log_info "kernel var kernel.pid_max config update: before=${old_pid_max}, target=200000"
else
log_info "kernel var kernel.pid_max config exists: before=${old_pid_max}, target=200000"
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

log_info "apply sysctl settings"
/sbin/sysctl -p
if [ $? -eq 0 ]; then
new_swappiness="$(sysctl -n vm.swappiness 2>/dev/null || echo "unknown")"
new_pid_max="$(sysctl -n kernel.pid_max 2>/dev/null || echo "unknown")"
log_info "sysctl -p success: vm.swappiness ${old_swappiness} -> ${new_swappiness}, kernel.pid_max ${old_pid_max} -> ${new_pid_max}"
else
log_error "sysctl -p failed"
fi
_exit`
