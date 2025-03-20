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

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType

MYSQL_COMMON_SQL_STATEMENTS = [
    {"name": _("查询链接信息"), "sql": "select * from information_schema.processlist limit 1;"},
    {"name": _("查看主从信息"), "sql": "show slave status;"},
    {"name": _("当前连接线程"), "sql": "show processlist;"},
    {"name": _("查询版本"), "sql": "show variables like 'version';"},
    {
        "name": _("查询字符集"),
        "sql": "select @@character_set_server as character_set_server, @@character_set_database as "
        "character_set_database;",
    },
    {"name": _("查询最大连接数"), "sql": "show variables like 'max_connections';"},
    {"name": _("查询binlog是否打开"), "sql": "show variables like 'log_bin';"},
    {"name": _("查询binlog格式"), "sql": "show variables like 'binlog_format';"},
    {
        "name": _("慢查询阈值"),
        "sql": "show variables like 'long_query_time';show variables like 'innodb_buffer_pool_size';show variables "
        "like 'innodb_data_file_path';",
    },
    {"name": _("库查询"), "sql": "show databases;"},
    {"name": _("已存在账户查询"), "sql": "select concat(User,'@',Host) from mysql.user;"},
    {
        "name": _("校验结果查询"),
        "sql": "select * from infodba_schema.checksum where this_crc<>master_crc or this_cnt<>master_cnt;",
    },
]

SQLSERVER__COMMON_SQL_STATEMENTS = []

DB_TYPE__COMMON_SQL_MAP = {
    DBType.MySQL.value: MYSQL_COMMON_SQL_STATEMENTS,
    DBType.TenDBCluster.value: MYSQL_COMMON_SQL_STATEMENTS,
    DBType.Sqlserver.value: SQLSERVER__COMMON_SQL_STATEMENTS,
}
