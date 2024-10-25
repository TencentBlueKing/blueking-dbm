"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.configuration.constants import DBType
from backend.flow.consts import DBA_ROOT_USER, WINDOW_SYSTEM_JOB_USER

os_script_language_map = {"linux": 1, "window": 5}

mysql_clear_machine_script = """
echo "clear mysql crontab...."
crontab -u mysql -r
echo "crontab completed"

echo "killing -9 mysql process ...."
ps uax | grep mysql-proxy | grep -v grep | awk -F ' ' '{print $2}' | xargs -i kill -9 {}
ps uax | grep mysql-crond | grep -v grep | awk -F ' ' '{print $2}' | xargs -i kill -9 {}
ps uax | grep mysqld | grep -v grep | awk -F ' ' '{print $2}' | xargs -i kill -9 {}
ps uax | grep exporter | grep -v grep | awk -F ' ' '{print $2}' | xargs -i kill -9 {}
echo "kill completed"

echo "rm home-mysql-dir ...."
if [ -d "/home/mysql" ]; then
    rm -rf /home/mysql/*
fi
echo "rm /home/mysql dir completed"

echo "rm data-dir ...."
if [ -d "/data" ]; then
    rm -rf /data/backup_stm/
    rm -rf /data/install/
    rm -rf /data/dbha/
    rm -rf /data/dbbak/
    rm -rf /data/mysqldata/
    rm -rf /data/mysqllog/
    rm -rf /data/mysql-proxy/
    rm -rf /data/idip_cache/
fi
echo "rm data-dir completed"

echo "rm data1-dir ...."
if [ -d "/data1" ]; then
    rm -rf /data1/mysqldata/
    rm -rf /data1/mysqllog/
    rm -rf /data1/dbbak/
    rm -rf /data1/dbha/
fi
echo "rm data1-dir completed"
"""

sqlserver_clear_machine_script = """
echo 1
"""


db_type_script_map = {
    DBType.MySQL.value: mysql_clear_machine_script,
    DBType.Sqlserver.value: sqlserver_clear_machine_script,
}

db_type_account_user_map = {
    DBType.MySQL.value: DBA_ROOT_USER,
    DBType.Sqlserver.value: WINDOW_SYSTEM_JOB_USER,
}
