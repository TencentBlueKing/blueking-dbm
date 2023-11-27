# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

drs_env_template = """
# 将证书移动到指定文件
mkdir -p /home/mysql/db-remote-service/
cp /data/install/server.crt /data/install/server.key /home/mysql/db-remote-service/

# 写入域名解析器的nameserver
# TODO: 后续需要把配置记录落库
sed -i '1i \
{{dns_nameserver}}' /etc/resolv.conf

# 以下为默认值
export DRS_TLS=true
export DRS_CONCURRENT=500
export DRS_MYSQL_ADMIN_PASSWORD="{{drs_password}}"
export DRS_MYSQL_ADMIN_USER="{{drs_user}}"
export DRS_PROXY_ADMIN_USER="proxy"
export DRS_PROXY_ADMIN_PASSWORD="{{proxy_password}}"
export DRS_PORT={{drs_port}}
export DRS_LOG_JSON=true # 是否使用 json 格式日志
export DRS_LOG_CONSOLE=true # 是否在 stdout 打印日志
export DRS_LOG_DEBUG=true # 启用 debug 日志级别
export DRS_KEY_FILE="/home/mysql/db-remote-service/server.key"


# 容器环境不要使用
export DRS_TMYSQLPARSER_BIN="tmysqlparse"
export DRS_LOG_FILE=test.log # 是否在文件打印日志, 文件路径
export DRS_LOG_FILE_ROTATE_SIZE=10 # rotate 大小, MB
export DRS_LOG_FILE_MAX_BACKUP=5 # 旧日志保留数
export DRS_LOG_FILE_MAX_AGE=5 # 过期天数
export DRS_CA_FILE=/home/mysql/db-remote-service/server.crt
export DRS_CERT_FILE=/home/mysql/db-remote-service/server.crt
export DRS_LOG_FILE_DIR=logs

# 下载SQL以及Parse临时结果存放处
export WORKDIR="/data"
"""

start_drs_service_template = """
path=/usr/local/bkdb;
mkdir -p $path

# 清除过时的drs相关文件
rm -rf $path/drs;
mkdir -p $path/drs;
cp /data/install/drs.env $path/drs;
cp /data/install/db-remote-service /data/install/tmysqlparse $path/drs;
cd $path/drs;

# 清理drs服务进程
drs_pid=`ps -aux | grep db-remote-service | grep -v grep | awk '{print $2}'`;
if [ "$drs_pid" != "" ]; then
    kill -9 $drs_pid;
fi

# 部署drs服务
chmod -R 777 $path/drs;
source drs.env;
nohup ./db-remote-service -> db-remote-service-apply.log 2>&1 &

# 验证部署是否成功
pid=$(lsof -i:$DRS_PORT | awk '{print $2}' | tail -n 1);
if [[ "$pid" != "" ]]; then
    echo "--------------------------drs process info---------------------";
    ps -ef | grep db-remote-service;
    echo "----------------------------------------------------------------";
    echo "DRS service deploys successfully!";
else
    echo "DRS service deployment encountered an error, Please check db-remote-service-apply.log";
    cat db-remote-service-apply.log
    exit 1
fi
"""

stop_drs_service_template = """
path=/usr/local/bkdb;

# 清理drs服务进程
drs_pid=`ps -aux | grep db-remote-service | grep -v grep | awk '{print $2}'`;
if [ "$drs_pid" != "" ]; then
    kill -9 $drs_pid;
fi

# 清理drs相关文件
rm -rf $path/drs;
"""
