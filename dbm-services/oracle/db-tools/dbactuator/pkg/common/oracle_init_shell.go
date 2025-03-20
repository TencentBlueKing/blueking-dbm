package common

// OracleShellInit 初始化os的shell脚本
var OracleShellInit = `#!/bin/sh
# 创建相关目录

function _exit() {
        rm $0
        exit
}

# 判断目录是否存在，如果不存在则创建，创建软链接 root执行
if [[ ! -d /data/install ]]
then
        mkdir -p /data/install
fi
chown -R {{user}}:{{group}} /data/install
chmod -R a+rwx /data/install
rm -rf /home/{{user}}/install
ln -s /data/install /home/{{user}}/install
chown -R {{user}}:{{group}} /home/{{user}}/install

_exit`
