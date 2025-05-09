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
    {"name": _("查询字符集"), "sql": "show variables like 'character_set%';"},
    {"name": _("查询最大连接数"), "sql": "show variables like 'max_connections';"},
    {"name": _("查询binlog是否打开"), "sql": "show variables like 'log_bin';"},
    {"name": _("查询binlog格式"), "sql": "show variables like 'binlog_format';"},
    {"name": _("慢查询阈值"), "sql": "show variables like 'long_query_time';"},
    {"name": _("库查询"), "sql": "show databases;"},
    {"name": _("innodb缓冲池大小"), "sql": "show variables like 'innodb_buffer_pool_size';"},
    {"name": _("innodb数据文件位置"), "sql": "show variables like 'innodb_data_file_path';"},
    {"name": _("库查询"), "sql": "show databases;"},
    {"name": _("已存在账户查询"), "sql": "select concat(User,'@',Host) from mysql.user limit 1000;"},
    {
        "name": _("校验结果查询"),
        "sql": "select count(*) from infodba_schema.checksum "
        "where this_crc<>master_crc or this_cnt<>master_cnt limit 1;",
    },
]

SQLSERVER__COMMON_SQL_STATEMENTS = [
    {
        "name": _("查询链接信息"),
        "sql": "select loginame,count(1) as cnt from master.sys.sysprocesses "
        "where loginame not in('sa','monitor','dbm_admin') and loginame not like 'mssql%'  "
        "and loginame not like '%\\%'  group by loginame;",
    },
    {
        "name": _("查看主从同步-镜像架构"),
        "sql": "select d.database_id,d.name,create_date,collation_name,state_desc,is_read_only,recovery_model_desc,"
        "m.mirroring_state_desc,mirroring_role_desc,mirroring_safety_level_desc,mirroring_partner_name,"
        "c.cntr_value as log_send_queue_kb from master.sys.databases d "
        "left join master.sys.database_mirroring m on m.database_id=d.database_id "
        "left join master.sys.dm_os_performance_counters c on d.name=c.instance_name and "
        "object_name LIKE '%Database Mirroring%'  AND c.counter_name='Log Send Queue KB' "
        "and c.instance_name not in('_Total') where m.database_id>4 and d.name not in('Monitor');",
    },
    {
        "name": _("查看主从同步-Alwayson架构"),
        "sql": "select d.database_id,d.name,create_date,collation_name,state_desc,is_read_only,recovery_model_desc,"
        "m.replica_id,r.replica_server_name,r.join_state_desc,s.role_desc,s.connected_state_desc,"
        "s.synchronization_health_desc,m.synchronization_state_desc,m.synchronization_health_desc,"
        "m.secondary_lag_seconds as log_send_queue_kb from master.sys.databases d "
        "left join master.sys.dm_hadr_database_replica_states m on m.database_id=d.database_id "
        "left join master.sys.dm_hadr_availability_replica_states s on m.replica_id=s.replica_id "
        "left join master.sys.dm_hadr_availability_replica_cluster_states r on m.replica_id=r.replica_id "
        "where m.database_id>4 and d.name not in('Monitor') order by database_id,role_desc;",
    },
]

DB_TYPE__COMMON_SQL_MAP = {
    DBType.MySQL.value: MYSQL_COMMON_SQL_STATEMENTS,
    DBType.TenDBCluster.value: MYSQL_COMMON_SQL_STATEMENTS,
    DBType.Sqlserver.value: SQLSERVER__COMMON_SQL_STATEMENTS,
}
