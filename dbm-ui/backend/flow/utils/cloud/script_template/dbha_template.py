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
# flake8: noqa

ha_gm_conf_template = """
log_conf:
  log_path: "./log"
  log_level: "LOG_DEBUG"
  log_maxsize: 512
  log_maxbackups: 1000
  log_maxage: 30
  log_compress: true
agent_conf:
  active_db_type: [
    "riak",
    "tendbha",
    "tendbcluster",
    "TwemproxyRedisInstance",
    "PredixyTendisplusCluster",
    "TwemproxyTendisSSDInstance",
    "PredixyRedisCluster",
    "RedisInstance",
    "MongoShardedCluster",
    "sqlserver_ha",
  ]
  city_id: {{city}}
  campus: "{{campus}}"
  cloud_id: {{cloud}}
  fetch_interval: 60
  reporter_interval: 120
  local_ip: "{{local_ip}}"
gm_conf:
  city_id: {{city}}
  campus: "{{campus}}"
  cloud_id: {{cloud}}
  liston_port: 50000
  local_ip: "{{local_ip}}"
  report_interval: 60
  GDM:
    dup_expire: 600
    scan_interval: 1
  GMM:
  GQA:
    idc_cache_expire: 300
    single_switch_idc: 50
    single_switch_interval: 86400
    single_switch_limit:  48
    all_host_switch_limit:  150
    all_switch_interval:  7200
  GCM:
    allowed_checksum_max_offset: 2
    allowed_slave_delay_max: 600
    allowed_time_delay_max: 300
    exec_slow_kbytes: 0
password_conf:
  host: "{{nginx_domain}}"
  port: 80
  url_pre: "/apis/proxypass"
  timeout: 10
  bk_conf:
    bk_token: "{{db_cloud_token}}"
db_conf:
  hadb:
    host: "{{nginx_domain}}"
    port: 80
    url_pre: "/apis/proxypass/hadb"
    timeout: 10
    bk_conf:
      bk_token: "{{db_cloud_token}}"
  cmdb:
    host: "{{nginx_domain}}"
    port: 80
    url_pre: "/apis/proxypass"
    timeout: 30
    bk_conf:
      bk_token: "{{db_cloud_token}}"
  mysql:
    user: "{{dbha_user}}"
    pass: "{{dbha_password}}"
    proxy_user: "proxy"
    proxy_pass: "{{proxy_password}}"
    timeout: 10
  redis:
    timeout: 10
  riak:
    timeout: 10
  mongodb:
    timeout: 5
  sqlserver:
    user: "mssql_dbha"
    pass: "{{dbha_password}}"
    timeout: 10
name_services:
  dns_conf:
    host: "{{nginx_domain}}"
    port: 80
    url_pre: "/apis/proxypass"
    user: "dbha"
    pass: "xxx"
    timeout: 10
    bk_conf:
      bk_token: "{{db_cloud_token}}"
  remote_conf:
    host: "{{nginx_domain}}"
    port: 80
    url_pre: "/apis/proxypass"
    user: "dbha"
    pass: "xxx"
    timeout: 10
    bk_conf:
      bk_token: "{{db_cloud_token}}"
  polaris_conf:
    host: "{{nginx_domain}}"
    port: 80
    user: "nouser"
    pass: "nopasswd"
    url_pre: "/apis/proxypass/nameservice"
    timeout: 10
    bk_conf:
      bk_token: "{{db_cloud_token}}"
  clb_conf:
    host: "{{nginx_domain}}"
    port: 80
    user: "nouser"
    pass: "nopasswd"
    url_pre: "/apis/proxypass/nameservice"
    timeout: 10
    bk_conf:
      bk_token: "{{db_cloud_token}}"
monitor:
  bk_data_id: {{mysql_crond_event_data_id}}
  access_token: "{{mysql_crond_event_data_token}}"
  beat_path: "{{mysql_crond_beat_path}}"
  agent_address: "{{mysql_crond_agent_address}}"
  local_ip: "{{local_ip}}"
ssh:
  max_uptime: 300
  port: 36000
  user: "mysql"
  pass: "{{mysql_os_password}}"
  sqlserver_ssh_user: "{{sqlserver_os_user}}"
  sqlserver_ssh_pass: "{{sqlserver_os_password}}"
  dest: "agent"
  timeout: 10
"""

ha_agent_conf_template = """
log_conf:
  log_path: "./log"
  log_level: "LOG_DEBUG"
  log_maxsize: 512
  log_maxbackups: 1000
  log_maxage: 30
  log_compress: true
agent_conf:
  active_db_type: [
    "riak",
    "tendbha",
    "tendbcluster",
    "TwemproxyRedisInstance",
    "PredixyTendisplusCluster",
    "TwemproxyTendisSSDInstance",
    "PredixyRedisCluster",
    "RedisInstance",
    "MongoShardedCluster",
    "sqlserver_ha",
  ]
  city_id: {{city}}
  campus: "{{campus}}"
  cloud_id: {{cloud}}
  fetch_interval: 60
  reporter_interval: 120
  local_ip: "{{local_ip}}"
gm_conf:
  city_id: {{city}}
  campus: "{{campus}}"
  cloud_id: {{cloud}}
  liston_port: 50000
  local_ip: "{{local_ip}}"
  report_interval: 60
  GDM:
    dup_expire: 600
    scan_interval: 1
  GMM:
  GQA:
    idc_cache_expire: 300
    single_switch_idc: 50
    single_switch_interval: 86400
    single_switch_limit:  48
    all_host_switch_limit:  150
    all_switch_interval:  7200
  GCM:
    allowed_checksum_max_offset: 2
    allowed_slave_delay_max: 600
    allowed_time_delay_max: 300
    exec_slow_kbytes: 0
password_conf:
  host: "{{nginx_domain}}"
  port: 80
  url_pre: "/apis/proxypass"
  timeout: 10
  bk_conf:
    bk_token: "{{db_cloud_token}}"
db_conf:
  hadb:
    host: "{{nginx_domain}}"
    port: 80
    url_pre: "/apis/proxypass/hadb"
    timeout: 10
    bk_conf:
      bk_token: "{{db_cloud_token}}"
  cmdb:
    host: "{{nginx_domain}}"
    port: 80
    url_pre: "/apis/proxypass"
    timeout: 30
    bk_conf:
      bk_token: "{{db_cloud_token}}"
  mysql:
    user: "{{dbha_user}}"
    pass: "{{dbha_password}}"
    proxy_user: "proxy"
    proxy_pass: "{{proxy_password}}"
    timeout: 10
  redis:
    timeout: 10
  riak:
    timeout: 10
  mongodb:
    timeout: 5
  sqlserver:
    user: "mssql_dbha"
    pass: "{{dbha_password}}"
    timeout: 10
name_services:
  dns_conf:
    host: "{{nginx_domain}}"
    port: 80
    url_pre: "/apis/proxypass"
    timeout: 10
    bk_conf:
      bk_token: "{{db_cloud_token}}"
  remote_conf:
    host: "{{nginx_domain}}"
    port: 80
    url_pre: "/apis/proxypass"
    timeout: 10
    bk_conf:
      bk_token: "{{db_cloud_token}}"
  polaris_conf:
    host: "{{nginx_domain}}"
    port: 80
    user: "nouser"
    pass: "nopasswd"
    url_pre: "/apis/proxypass/nameservice"
    timeout: 10
    bk_conf:
      bk_token: "{{db_cloud_token}}"
  clb_conf:
    host: "{{nginx_domain}}"
    port: 80
    user: "nouser"
    pass: "nopasswd"
    url_pre: "/apis/proxypass/nameservice"
    timeout: 10
    bk_conf:
      bk_token: "{{db_cloud_token}}"
monitor:
  bk_data_id: {{mysql_crond_event_data_id}}
  access_token: "{{mysql_crond_event_data_token}}"
  beat_path: "{{mysql_crond_beat_path}}"
  agent_address: "{{mysql_crond_agent_address}}"
  local_ip: "{{local_ip}}"
ssh:
  max_uptime: 300
  port: 36000
  user: "mysql"
  pass: "{{mysql_os_password}}"
  sqlserver_ssh_user: "{{sqlserver_os_user}}"
  sqlserver_ssh_pass: "{{sqlserver_os_password}}"
  dest: "agent"
  timeout: 10
"""

dbha_start_script_template = """
path=/usr/local/bkdb;

# 删除旧dbha服务(注意根据部署的dbha_conf删除，因为可能一台机器同时部署着gm和agent)
dbha_pid=`ps -aux | grep {{dbha_conf}} | grep -v grep | awk '{print $2}'`;
if [ "$dbha_pid" != "" ]; then
    kill -9 $dbha_pid;
fi
# 备份上次的二进制和日志
mv $path/dbha/{{dbha_type}} $path/dbha/old_{{dbha_type}}

# 准备相关文件
mkdir -p $path/dbha/{{dbha_type}};
cp /data/install/{{dbha_conf}} $path/dbha/{{dbha_type}};
cp /data/install/dbha $path/dbha/{{dbha_type}};
chmod -R 777 $path/dbha;
systemctl start ntpd
systemctl enable ntpd

# 部署dbha服务
cd $path/dbha/{{dbha_type}}
nohup ./dbha -config_file={{dbha_conf}} -type={{dbha_type}} -> dbha-apply.log 2>&1 &
echo "--------------------------dbha process info---------------------";
ps -ef | grep dbha;
echo "----------------------------------------------------------------";

# 增加定期拉起任务
dbha_cron="$path/dbha/{{dbha_type}}/cron.sh";
echo -e "
# 检查进程是否存在
is_process_running() {
    ps aux | grep {{dbha_conf}} | grep -v grep | awk '{print \$2}' > /dev/null
}
if ! is_process_running; then
    echo "Process {{dbha_type}} is not running. Restarting..."
    cd /usr/local/bkdb/dbha/{{dbha_type}}
    # 启动进程的命令
    nohup ./dbha -config_file=ha-{{dbha_type}}.conf -type={{dbha_type}} -> dbha-apply.log 2>&1 &
    echo "Process {{dbha_type}} restarted successfully."
fi
" > $dbha_cron

chmod +x $dbha_cron;
(crontab -l ; echo "* * * * * $dbha_cron") 2>&1 | grep -v "no crontab" | sort | uniq | crontab -
"""

dbha_stop_script_template = """
path=/usr/local/bkdb;

dbha_pid=`ps -aux | grep {{dbha_conf}} | grep -v grep | awk '{print $2}'`;
if [ "$dbha_pid" != "" ]; then
    kill -9 $dbha_pid;
fi
rm -rf $path/dbha/{{dbha_type}}
"""
