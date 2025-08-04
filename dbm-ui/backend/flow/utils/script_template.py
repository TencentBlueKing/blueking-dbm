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
# fast_execute_script 滚动配置配置，先定义后续考虑使用
fast_execute_script_rolling_config = {
    # 一批最大滚动机器数量
    "expression": 1000,
    # 滚动机制,1-执行失败则暂停；2-忽略失败，自动滚动下一批；3-人工确认
    "mode": 1,
}

# fast_execute_script接口固定参数
fast_execute_script_common_kwargs = {
    "timeout": 3600,
    "account_alias": "root",
    "is_param_sensitive": 1,
}

# fast_transfer_file接口固定参数
fast_transfer_file_common_kwargs = {
    "account_alias": "root",
}

# mysql actuator 执行的shell命令，引入文件MD5值的比较，避免并发执行过程中输出错误信息，误导日志的捕捉
actuator_template = """
find /data/install/ -maxdepth 1  -type d -name "dbactuator-*"  -mtime +90 |xargs -i rm -r {}  2>/dev/null || true 
find /data/install/dbactuator-*/ -mtime +10 -name dbactuator -delete 2>/dev/null || true
lock_file="/tmp/dbm-mysql-{{uid}}.lock"
trap 'rm -f "$lock_file"' EXIT
(
   flock -w 10 200 || { echo "Another process is holding the lock. Exiting."; exit 1; }
   mkdir -p /data/install/dbactuator-{{uid}}/logs
   if [[ ! -f /data/install/dbactuator-{{uid}}/dbactuator ]];then
      cp /data/install/dbactuator /data/install/dbactuator-{{uid}}
   else
      md5_1=`md5sum /data/install/dbactuator | cut -d ' ' -f1 `
      md5_2=`md5sum /data/install/dbactuator-{{uid}}/dbactuator | cut -d ' ' -f1`
      if [[ ${md5_1} != ${md5_2} ]];then
         cp /data/install/dbactuator /data/install/dbactuator-{{uid}}
      fi
   fi
)  200>"$lock_file"
   rm -f "$lock_file"
   cd /data/install/dbactuator-{{uid}}
   chmod +x dbactuator
   ./dbactuator {{db_type}} {{action}} --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} --version_id {{version_id}} --payload $1 {% for item in non_sensitive_payload %} -c {{ item }} {% endfor %}

"""  # noqa

# riak actuator 执行的shell命令，引入文件MD5值的比较，避免并发执行过程中输出错误信息，误导日志的捕捉
riak_actuator_template = """
find /data/install/ -maxdepth 1  -type d -name "dbactuator-*"  -mtime +90 |xargs -i rm -r {};
find /data/install/dbactuator-*/ -mtime +10 -name dbactuator -delete
mkdir -p /data/install/dbactuator-{{uid}}/logs
if [[ ! -f /data/install/dbactuator-{{uid}}/dbactuator ]];then
   cp /data/install/dbactuator /data/install/dbactuator-{{uid}}

else
   md5_1=`md5sum /data/install/dbactuator | cut -d ' ' -f1 `
   md5_2=`md5sum /data/install/dbactuator-{{uid}}/dbactuator | cut -d ' ' -f1`
   if [[ ${md5_1} != ${md5_2} ]];then
      cp /data/install/dbactuator /data/install/dbactuator-{{uid}}
   fi
fi
cd /data/install/dbactuator-{{uid}}
chmod +x dbactuator
./dbactuator {{db_type}} {{action}} --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} --version_id {{version_id}} --payload $1
"""  # noqa

# 运行dba_toolkit的命令
dba_toolkit_actuator_template = """
cd /home/mysql/dba-toolkit
chmod +x dbactuator
./dbactuator {{db_type}} {{action}} --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload-format=raw --payload {{payload}}
"""

# 运行权限刷新的dba_tookit命令
privilege_flush_template = """
cd /home/mysql/dba-toolkit
chmod +x dbactuator
echo privilege: {{access_hosts}}-{{usr}}--{{pwd}}; type: {{type}}
echo Test privilege flush successfully!
"""

# 在powershell 环境下 执行 sqlserver actuator 命令
# 每个单据下创建单据目录，避免并发时的文件冲突
# 同时对比actuator的md5,如果一致则不发，提供效率
sqlserver_actuator_template = """
param (
    [string]$general_payload
)
$extend_payload = "{{extend_payload}}"
$targetDir = "d:\\install\\dbactuator-{{uid}}"
$logDir = Join-Path $targetDir "logs"
$sourceFile = "d:\\install\\dbactuator.exe"

# Create logs directory if it doesn't exist
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Set-Location $targetDir
$tempFile = "extend_payload_{{node_id}}.tmp"
$extend_payload | Set-Content -Path $tempFile -Force

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Unrestricted -Force
..\\dbactuator.exe  {{db_type}} {{action}} --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} --version_id \
{{version_id}}  --general_payload $general_payload --extend_payload_file $tempFile

if ($LASTEXITCODE -ne 0 ) {
exit 1
}
"""
