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

from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, MachineType, TenDBClusterSpiderRole

mysql_cluster_type_choices = [
    (ClusterType.TenDBSingle.value, ClusterType.TenDBSingle.name),
    (ClusterType.TenDBHA.value, ClusterType.TenDBHA.name),
    (ClusterType.TenDBCluster.value, ClusterType.TenDBCluster.name),
]

mysql_machine_type_choices = [
    (MachineType.SINGLE.value, MachineType.SINGLE.name),
    (MachineType.BACKEND.value, MachineType.BACKEND.name),
    (MachineType.REMOTE.value, MachineType.REMOTE.name),
    (MachineType.SPIDER.value, MachineType.SPIDER.name),
]

mysql_instance_role_choices = [
    (InstanceRole.BACKEND_MASTER.value, InstanceRole.BACKEND_MASTER.name),
    (InstanceRole.BACKEND_SLAVE.value, InstanceRole.BACKEND_SLAVE.name),
    (InstanceRole.REMOTE_MASTER.value, InstanceRole.REMOTE_MASTER.name),
    (InstanceRole.REMOTE_SLAVE.value, InstanceRole.REMOTE_SLAVE.name),
    (TenDBClusterSpiderRole.SPIDER_MASTER, TenDBClusterSpiderRole.SPIDER_MASTER.name),
]

# 容量采集场景使用的角色（覆盖 tendbsingle 的 orphan、tendbha/tendbcluster 的 master/slave）
mysql_capacity_inner_role_choices = [
    (InstanceInnerRole.SLAVE.value, InstanceInnerRole.SLAVE.name),
    (InstanceInnerRole.MASTER.value, InstanceInnerRole.MASTER.name),
    (InstanceInnerRole.ORPHAN.value, InstanceInnerRole.ORPHAN.name),
]

# mysql_slave_status_masks = [
#     "Master_User",
#     "Master_SSL_Allowed",
#     "Master_SSL_CA_File",
#     "Master_SSL_CA_Path",
#     "Master_SSL_Cert",
#     "Master_SSL_Cipher",
#     "Master_SSL_Key",
#     "Master_TLS_Version",
#     "Relay_Log_Space",
#     "Master_SSL_Verify_Server_Cert",
#     "Master_UUID",
#     "Master_Info_File",
#     "Master_Retry_Count",
#     "Master_Bind",
#     "Master_SSL_Crl",
#     "Master_SSL_Crlpath",
#     "Connect_Retry",
#     "Replicate_Ignore_Server_Ids",
#     "Last_IO_Error_Timestamp",
#     "Last_SQL_Error_Timestamp",
#     "Until_Condition",
#     "Until_Log_File",
#     "Until_Log_Pos",
#     "Skip_Counter",
#     "Channel_Name",
# ]

mysql_metric_name_choices = [
    ("cpu_summary", _("cpu 负载")),
    ("qps_summary", _("qps 请求量")),
    ("memory_usage", _("memory 内存使用率")),
    ("slow_count", _("slowlog 慢日志数量")),
    ("threads_running", _("threads 线程数 趋势")),
    ("connections", _("连接数 趋势")),
    ("disk_used", _("磁盘使用量")),
    ("disk_total", _("磁盘总量")),
    ("disk_usage", _("磁盘使用率")),
]


# class MySQLProcessListInstanceGroupType(StrStructuredEnum):
#     MasterGroup = EnumField("master_group", _("主分组"))
#     SlaveGroup = EnumField("slave_group", _("从分组"))


# class MySQLProcessListFilterFieldType(StrStructuredEnum):
#     AccessSourceAddress = EnumField("access_source_address", _("访问来源地址"))
#     ProxyAddress = EnumField("proxy_address", _("接入层地址"))
#     StorageAddress = EnumField("mysql_address", _("存储层地址"))
#     Command = EnumField("command", _("正在执行的命令操作"))
#     User = EnumField("user", _("访问账号"))
#     DB = EnumField("db", _("访问 DB 名"))
#     State = EnumField("state", _("连接状态"))
#     Time = EnumField("time", _("连接持续时长, 单位是秒"))


# class MySQLProcessListFilterOpType(StrStructuredEnum):
#     OpIn = EnumField("in", _("包含, 是, 存在"))
#     OpNotIn = EnumField("not in", _("不包含, 不是, 不存在"))
#     OpGt = EnumField(">", _("大于"))
#     OpLt = EnumField("<", _("小于"))
#     OpGte = EnumField(">=", _("大于等于"))
#     OpLte = EnumField("<=", _("小于等于"))


mysql_slowlog_metric_name_choices = [
    ("query_time", _("按查询执行时间排序聚合")),
    ("slow_count", _("按照慢查询数量排序聚合")),
    ("rows_scan", _("按照查询扫描行数排序聚合")),
]

mysql_slowlog_orderby_choices = [
    ("count_star", _("按一类 sql (指纹)查询次数排序")),
    ("query_time_max", _("单 sql 最大查询时间")),
    ("query_time_sum", _("一类 sql 总查询时间")),
    ("rows_examined_max", _("单 sql 最大扫描行数")),
    ("rows_examined_sum", _("一类 sql 总扫描行数")),
    ("rows_sent_max", _("单 sql 最大返回行数")),
    ("rows_sent_sum", _("一类 sql 总返回行数")),
]

mysql_config_update_allowed = [
    ("backup", _("备份配置")),
    ("mysql_monitor", _("监控配置")),
    ("checksum", _("校验配置")),
]
