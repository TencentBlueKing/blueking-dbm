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

# 启用dns服务的部署脚本
start_dns_service_template = """
# dns部署路径就是/usr/local，修改可能造成部署失败
path=/usr/local;
mkdir -p $path

# kill原来的bind服务
bind_pid=`ps -aux | grep bind | grep -v grep | awk '{print $2}'`;
if [ "$bind_pid" != "" ]; then
    kill -9 $bind_pid;
fi
rm -rf $path/bind9;
rm -rf $path/bind;

# 启动bind服务
tar -xvf /data/install/bind.tar.gz -C $path;
ln -s $path/bind9 $path/bind;
chown -R root:root $path/bind/*
nohup $path/bind/sbin/named -4 > $path/bind/bind-apply.log 2>&1 &

# 验证bind服务可用性
echo "--------------------------bind process info---------------------";
ps -ef | grep bind;
echo "----------------------------------------------------------------";

old_db_ip="1.1.1.1";
ips=`ifconfig -a|grep inet|grep -v 127.0.0.1|grep -v inet6|awk '{print $2}'|tr -d "addr:"`;
check_bind(){
    for ip in $ips;
    do
        res=`dig +short dns.test.dba.db @$ip`;
        if [ $res != $1 ]; then
            echo "Error, expected $1, actual output is $res";
            exit 1;
        else
            echo "Successfully! $res";
        fi
    done
}
check_bind $old_db_ip;

# 修改验证
new_db_ip="1.1.1.2";
sed -i "s/$old_db_ip/$new_db_ip/g" $path/bind/var/run/named/db;
$path/bind/sbin/rndc reload;
check_bind $new_db_ip;

sed -i "s/$new_db_ip/$old_db_ip/g" $path/bind/var/run/named/db;
$path/bind/sbin/rndc reload;

# kill原来的pull-crond服务
pull_crond_pid=`ps -aux | grep pull-crond | grep -v grep | awk '{print $2}'`;
if [ "$pull_crond_pid" != "" ]; then
    kill -9 $pull_crond_pid;
fi

# 配置pull-crond服务的文件路径
cp /data/install/pull-crond $path/bind/admin;
cp /data/install/pull-crond.conf $path/bind/admin;

# 写入dns相关信息，过滤掉无法ping通的IP
DNS_LIST=$(awk 'BEGIN{ORS=" "} $1=="nameserver" {print $2}' /etc/resolv.conf);
if ! grep -q "nameserver.*127.0.0.1" /etc/resolv.conf; then
    DNS_LIST+=(127.0.0.1);
fi

available_ips=""
for ip in $DNS_LIST
do
  if timeout 2 ping -c 1 "$ip" >/dev/null 2>&1; then
    available_ips+="$ip "
  fi
done

DNS_LIST=${available_ips// /;};
sed -i "s/forward_ip=.*/forward_ip="$DNS_LIST"/" $path/bind/admin/pull-crond.conf;

# 启动pull-crond服务
cd $path/bind/admin/;
chmod 777 pull-crond;
nohup ./pull-crond -c pull-crond.conf > pull-crond-apply.log 2>&1 &
if [ $? != 0 ]; then
    echo "Error, a exception occurs in the pull-crond service deployment";
    cat pull-crond-apply.log;
    exit 1;
fi

echo "--------------------------pull-crond process info---------------------";
ps -ef | grep pull-crond;
echo "----------------------------------------------------------------";
echo "Successfully! Pull-crond process has setup";

# 增加定时拉起命令
crontab -l > crontab_backup.txt
command="* * * * * cd $path/bind/admin; /bin/sh check_dns_and_pull_crond.sh 1>/dev/null 2>&1"

if crontab -l | grep -Fxq "$command"; then
    echo "Scheduled pull task already exists, ignore..."
else
    (crontab -l ; echo "$command") | uniq - | crontab -
    echo "Pull up task has been added to crontab。"
fi
"""

# forward_ip会在执行脚本的时候填充
dns_pull_crond_conf_template = """
info_log_path="../log/info.log"
error_log_path="../log/err.log"

db_cloud_token="{{db_cloud_token}}"
bk_dns_api_url="http://{{nginx_domain}}"
bk_cloud_id="{{bk_cloud_id}}"

data_id={{data_id}}
access_token="{{access_token}}"
bkmonitorbeat="{{bkmonitor_beat_path}}"
agent_address="{{agent_address}}"

interval="3"
flush_switch="true"
forward_ip=""

options_named_file="/usr/local/bind/etc/named.conf"
options_named_file_tpl="/usr/local/bind/etc/named.conf_tpl"
local_named_file="/usr/local/bind/etc/named.conf.local"
zone_dir_path="/usr/local/bind/var/run/named/"
rndc="/usr/local/bind/sbin/rndc"
rndc_config="/usr/local/bind/etc/rndc.conf"
"""

# nameserver刷新脚本 TODO: fake脚本，占位用
dns_flush_templace = """
echo nameserver: {{dns_ips}}
echo flush_type: {{flush_type}}
echo nameserver flush successfully!
"""

# dns裁撤
stop_dns_server_template = """
path=/usr/local;

bind_pid=`ps -aux | grep bind | grep -v grep | awk '{print $2}'`;
if [ "$bind_pid" != "" ]; then
    kill -9 $bind_pid;
fi
pull_crond_pid=`ps -aux | grep pull-crond | grep -v grep | awk '{print $2}'`;
if [ "$pull_crond_pid" != "" ]; then
    kill -9 $pull_crond_pid;
fi
rm -rf $path/bind9;
rm -rf $path/bind;
"""
