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
from backend.db_meta.enums import ClusterType, MachineType
from blue_krill.data_types.enum import EnumField, StructuredEnum

UNIFY_QUERY_PARAMS = {
    "bk_biz_id": 3,
    "query_configs": [
        {
            "data_source_label": "prometheus",
            "data_type_label": "time_series",
            "promql": "",
            "interval": 60,
            "alias": "a",
        }
    ],
    "expression": "a",
    "alias": "a",
    # 单位：s
    "start_time": 1697100405,
    "end_time": 1697101305,
    "slimit": 500,
    "down_sample_range": "1s",
    # 取最新的几个周期，可以加速查询（如果指标数据不连续，则查不出数据）
    "type": "instant",
}

EXPORTER_UP_QUERY_TEMPLATE = {
    DBType.Redis: {
        "range": 5,
        "dbm_redis_exporter": """count by (cluster_domain) (
            bkmonitor:exporter_dbm_redis_exporter:redis_up{instance_role='redis_master'}
        )""",
    }
}

QUERY_TEMPLATE = {
    ClusterType.TendisTwemproxyRedisInstance: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            bkmonitor:exporter_dbm_redis_exporter:redis_memory_used_bytes{instance_role="redis_master",%s}
           )""",
        "total": """sum by (cluster_domain) (
            avg by (cluster_domain, bk_target_ip) (
                    bkmonitor:dbm_system:mem:total{instance_role="redis_master",%s}
            ))""",
    },
    ClusterType.TwemproxyTendisSSDInstance: {
        "range": 5,
        "used": """sum by (cluster_domain) (max by (cluster_domain,ip,mount_point) (
        bkmonitor:exporter_dbm_redis_exporter:redis_datadir_df_used_mb{instance_role="redis_master",%s} * 1024 * 1024
        ))""",
        "total": """sum by (cluster_domain) (max by (cluster_domain,ip,mount_point) (
        bkmonitor:exporter_dbm_redis_exporter:redis_datadir_df_total_mb{instance_role="redis_master",%s} * 1024 *
        1024))""",
    },
    ClusterType.TenDBSingle: {
        "range": 129,
        "used": """sum by (cluster_domain) (
                    max_over_time(
                        bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_used_mb{instance_role="orphan",%s}[5m]
                    ) * 1024 * 1024 )""",
        "total": """max by (cluster_domain) (
                    max_over_time(
                        bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{instance_role="orphan",%s}[5m]
                    ) * 1024 * 1024 )""",
    },
    ClusterType.TenDBHA: {
        "range": 129,
        "used": """sum by (cluster_domain) (
            max by (cluster_domain, ip) (
                max_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_used_mb{instance_role="backend_master",%s}[124m]
                ) * 1024 * 1024
            ))""",
        "total": """sum by (cluster_domain) (
            max by (cluster_domain, ip) (
                max_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{instance_role="backend_master",%s}[124m]
                ) * 1024 * 1024
            ))""",
    },
    ClusterType.TenDBCluster: {
        "range": 129,
        "used": """sum by (cluster_domain) (
            avg by (cluster_domain, instance) (
                avg_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_du_used_mb{instance_role="remote_master",%s}[124m]
                ) * 1024 * 1024))""",
        "total": """sum by (cluster_domain) (
            avg by (cluster_domain, ip) (
                avg_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{instance_role="remote_master",%s}[124m]
                ) * 1024 * 1024))""",
    },
    ClusterType.SqlserverSingle: {
        "range": 120,
        "used": """sum by (cluster_domain) (
                    max_over_time(
                        bkmonitor:exporter_dbm_mssql_exporter:mssql_datadisk_used{instance_role="orphan",%s}[5m]
                    ) * 1024 * 1024 * 1024 )""",
        "total": """max by (cluster_domain) (
                    max_over_time(
                        bkmonitor:exporter_dbm_mssql_exporter:mssql_datadisk_total{instance_role="orphan",%s}[5m]
                    ) * 1024 * 1024 * 1024 )""",
    },
    ClusterType.SqlserverHA: {
        "range": 120,
        "used": """sum by (cluster_domain) (
            max by (cluster_domain, ip) (
                max_over_time(
                    bkmonitor:exporter_dbm_mssql_exporter:mssql_datadisk_used{instance_role="backend_master",%s}[5m]
                ) * 1024 * 1024 * 1024
            ))""",
        "total": """sum by (cluster_domain) (
            max by (cluster_domain, ip) (
                max_over_time(
                    bkmonitor:exporter_dbm_mssql_exporter:mssql_datadisk_total{instance_role="backend_master",%s}[5m]
                ) * 1024 * 1024 * 1024
            ))""",
    },
    # es采集器本身存在容量统计指标（elasticsearch_filesystem_data_size_bytes、elasticsearch_indices_store_size_bytes）
    # 但数据节点只注册了一个，这里暂时用磁盘容量计算
    ClusterType.Es: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            max by (cluster_domain,bk_target_ip)(
                sum by (cluster_domain,bk_target_ip, instance_port)(bkmonitor:dbm_system:disk:used{
                    device_type=~"ext.?|xfs",
                    instance_role=~"^(es_datanode_hot|es_datanode_cold)$",
                    mount_point!~"^(/|/usr/local)$",%s
                    }
                )))""",
        "total": """sum by (cluster_domain) (
            max by (cluster_domain,bk_target_ip)(
                sum by (cluster_domain,bk_target_ip, instance_port)(bkmonitor:dbm_system:disk:total{
                    device_type=~"ext.?|xfs",
                    instance_role=~"^(es_datanode_hot|es_datanode_cold)$",
                    mount_point!~"^(/|/usr/local)$",%s
                }
            )))""",
    },
    ClusterType.Kafka: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            max_over_time(
                bkmonitor:dbm_system:disk:used{
                    device_type=~"ext.?|xfs",instance_role="broker",mount_point!~"^(/|/usr/local)$",%s
                }[5m]
            ))""",
        "total": """sum by (cluster_domain) (
            max_over_time(
                bkmonitor:dbm_system:disk:total{
                    device_type=~"ext.?|xfs",
                    instance_role="broker",
                    mount_point!~"^(/|/usr/local)$",%s
                }[5m]
            ))""",
    },
    ClusterType.Pulsar: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            max_over_time(
                bkmonitor:dbm_system:disk:used{
                    device_type=~"ext.?|xfs",
                    instance_role="pulsar_bookkeeper",
                    mount_point!~"^(/|/usr/local)$",%s
                }[5m]
            ))""",
        "total": """sum by (cluster_domain) (
            max_over_time(
                bkmonitor:dbm_system:disk:total{
                    device_type=~"ext.?|xfs",
                    instance_role="pulsar_bookkeeper",
                    mount_point!~"^(/|/usr/local)$",%s
                }[5m]
            ))""",
    },
    ClusterType.Hdfs: {
        "range": 5,
        "used": """avg by (cluster_domain) (
                    avg_over_time(bkmonitor:exporter_dbm_hdfs_exporter:hadoop_namenode_capacity_used{%s}[5m]))""",
        "total": """avg by (cluster_domain) (
                    avg_over_time(bkmonitor:exporter_dbm_hdfs_exporter:hadoop_namenode_capacity_total{%s}[5m]))""",
    },
    ClusterType.Influxdb: {
        "range": 5,
        "used": """max by (instance_host) (
            max_over_time(bkmonitor:pushgateway_dbm_influxdb_bkpull:disk_used{path=~"^/data|/data1$",%s}[5m]))""",
        "total": """max by (instance_host) (
            max_over_time(bkmonitor:pushgateway_dbm_influxdb_bkpull:disk_total{path=~"^/data|/data1$",%s}[5m]))""",
    },
    ClusterType.Dbmon: {
        "range": 5,
        "heartbeat": """
        avg by (target,bk_biz_id,app,bk_cloud_id, cluster_domain, cluster_type, instance_role)
        (avg_over_time(custom:dbm_report_channel:redis_dbmon_heart_beat{
            {cluster_domain="{cluster_domain}",%s}
        }[1m]))""",
    },
}

# 使用相同容量查询模板的集群类型映射
SAME_QUERY_TEMPLATE_CLUSTER_TYPE_MAP = {
    # Redis 内存型
    ClusterType.TendisPredixyRedisCluster.value: ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.RedisInstance.value: ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TendisRedisInstance.value: ClusterType.TendisTwemproxyRedisInstance.value,
    ClusterType.TendisRedisCluster.value: ClusterType.TendisTwemproxyRedisInstance.value,
    # Redis 磁盘型
    ClusterType.TendisPredixyTendisplusCluster.value: ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisTwemproxyTendisplusIns.value: ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisTendisSSDInstance.value: ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisTendisplusInsance.value: ClusterType.TwemproxyTendisSSDInstance.value,
    ClusterType.TendisTendisplusCluster.value: ClusterType.TwemproxyTendisSSDInstance.value,
}

# Redis组件负载表达式模板
REDIS_LOAD_QUERY_TEMPLATE = {
    # predixy 主机cpu
    "predixy_host_cpu": "max by (cluster_domain,ip) (max_over_time(bkmonitor:dbm_system:cpu_summary:usage{"
    'cluster_domain=~"{cluster_domains}",instance_role="proxy"}[1m]))',
    # twemproxy实例cpu
    "twemproxy_instance_cpu": "sum by(cluster_domain,instance_host) (irate("
    'bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_process_cpu{cluster_domain=~"{'
    'cluster_domains}"}[1m]))/100',
    # 主机cpu使用率
    "redis_host_cpu": "max by (cluster_domain,ip) (max_over_time(bkmonitor:dbm_system:cpu_summary:usage{"
    'cluster_domain=~"{cluster_domains}",instance_role="redis_master"}[1m]))',
    # 主机磁盘使用率
    "redis_host_disk": "max by (cluster_domain,bk_target_cloud_id) ("
    'bkmonitor:exporter_dbm_redis_exporter:redis_datadir_df_usage{cluster_domain="{'
    'cluster_domain}",instance_role="redis_master"})',
    # "主机io"
    "redis_host_io": "max by (cluster_domain,ip) (max_over_time(bkmonitor:dbm_system:io:util{"
    'cluster_domain=~"{cluster_domains}",instance_role="redis_master"}[1m]))',
    # redis主机内存使用率
    "redis_host_mem": "max by (cluster_domain,ip) (max_over_time(bkmonitor:dbm_system:mem:pct_used{"
    'cluster_domain=~"{cluster_domains}",instance_role="redis_master"}[1m]))',
    # redis proxy主机内存使用率
    "proxy_host_mem": 'max by (cluster_domain,ip) (max_over_time(bkmonitor:dbm_system:mem:pct_used{cluster_domain="{'
    'cluster_domain}",instance_role="proxy"}[1m]))',
    # redis连接数
    "redis_connections": "sum by (cluster_domain,instance) ("
    'bkmonitor:exporter_dbm_redis_exporter:redis_connected_clients{cluster_domain="{'
    'cluster_domain}",instance_role="redis_master"})',
    # predixy连接数
    "predixy_connections": "sum by (cluster_domain,instance_host) (bkmonitor:exporter_dbm_predixy_exporter"
    ':predixy_cluster_connections{cluster_domain=~"{cluster_domains}"})',
    # twemproxy连接数
    "twemproxy_connections": "sum by (cluster_domain,instance_host) (bkmonitor:exporter_dbm_twemproxy_exporter"
    ':twemproxy_connections_curr{cluster_domain=~"{cluster_domains}"})',
}

# 集群机器负载查询组合字典
CLUSTER_MACHINE_LOAD_QUERY_TEMPLATE = {
    MachineType.REDIS: {
        "cpu": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_cpu"], "max": 60, "min": 20},
        "mem": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_mem"], "max": 70, "min": 20},
        "connections": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_connections"], "max": 20000, "min": 2000},
    },
    MachineType.TWEMPROXY: {
        "cpu": {"promql": REDIS_LOAD_QUERY_TEMPLATE["twemproxy_instance_cpu"], "max": 60, "min": 20},
        "mem": {"promql": REDIS_LOAD_QUERY_TEMPLATE["proxy_host_mem"], "max": 70, "min": 20},
        "connections": {"promql": REDIS_LOAD_QUERY_TEMPLATE["twemproxy_connections"], "max": 20000, "min": 2000},
    },
    MachineType.PREDIXY: {
        "cpu": {"promql": REDIS_LOAD_QUERY_TEMPLATE["predixy_host_cpu"], "max": 60, "min": 20},
        "mem": {"promql": REDIS_LOAD_QUERY_TEMPLATE["proxy_host_mem"], "max": 70, "min": 20},
        "connections": {"promql": REDIS_LOAD_QUERY_TEMPLATE["predixy_connections"], "max": 20000, "min": 2000},
    },
    MachineType.TENDISSSD: {
        "cpu": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_cpu"], "max": 60, "min": 20},
        "mem": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_mem"], "max": 70, "min": 20},
        "disk": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_disk"], "max": 20000, "min": 2000},
        "io": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_io"], "max": 20000, "min": 2000},
    },
    MachineType.TENDISPLUS: {
        "cpu": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_cpu"], "max": 60, "min": 20},
        "mem": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_mem"], "max": 85, "min": 20},
        "disk": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_disk"], "max": 20000, "min": 2000},
        "io": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_host_io"], "max": 20000, "min": 2000},
        "connections": {"promql": REDIS_LOAD_QUERY_TEMPLATE["redis_connections"], "max": 20000, "min": 2000},
    },
}

CLUSTER_TYPE_LOAD_RULES = {
    ClusterType.RedisInstance: [MachineType.REDIS],
    ClusterType.TendisTwemproxyRedisInstance: [MachineType.REDIS, MachineType.TWEMPROXY],
    ClusterType.TendisPredixyRedisCluster: [MachineType.REDIS, MachineType.PREDIXY],
    ClusterType.TendisPredixyTendisplusCluster: [MachineType.TENDISPLUS, MachineType.PREDIXY],
    ClusterType.TwemproxyTendisSSDInstance: [MachineType.TENDISSSD, MachineType.TWEMPROXY],
}


class RedisLoadStatus(str, StructuredEnum):
    LOW = EnumField("low", _("低负载"))
    HIGH = EnumField("high", _("高负载"))
