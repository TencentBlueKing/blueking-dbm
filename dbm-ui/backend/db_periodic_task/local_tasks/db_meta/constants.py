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

from backend.db_meta.enums import ClusterType

UNIFY_QUERY_PARAMS = params = {
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
    # 取最新的几个周期，可以加速查询
    "type": "instant",
}

QUERY_TEMPLATE = {
    ClusterType.TendisTwemproxyRedisInstance: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            sum_over_time(
                bkmonitor:exporter_dbm_redis_exporter:redis_memory_used_bytes{ instance_role="redis_master"}[1m]
            ))""",
        "total": """sum by (cluster_domain) (
            avg by (cluster_domain, bk_target_ip) (
                avg_over_time(
                    bkmonitor:dbm_system:mem:total{instance_role="redis_master"}[1m]
                )
            ))""",
    },
    ClusterType.TwemproxyTendisSSDInstance: {
        "range": 5,
        "used": """sum by (cluster_domain) (max by (cluster_domain,ip,mount_point) (
            max_over_time(
                bkmonitor:exporter_dbm_redis_exporter:redis_datadir_df_used_mb{instance_role="redis_master"}[1m]
            ) * 1024 * 1024))""",
        "total": """sum by (cluster_domain) (max by (cluster_domain,ip,mount_point) (
            max_over_time(
                bkmonitor:exporter_dbm_redis_exporter:redis_datadir_df_total_mb{instance_role="redis_master"}[1m]
            ) * 1024 * 1024))""",
    },
    ClusterType.TenDBSingle: {
        "range": 15,
        "used": """sum by (cluster_domain) (
                    max_over_time(
                        bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_used_mb{instance_role="orphan"}[5m]
                    ) * 1024 * 1024 )""",
        "total": """max by (cluster_domain) (
                    max_over_time(
                        bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{instance_role="orphan"}[5m]
                    ) * 1024 * 1024 )""",
    },
    ClusterType.TenDBHA: {
        "range": 15,
        "used": """sum by (cluster_domain) (
            max by (cluster_domain, ip) (
                max_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_used_mb{instance_role="backend_master"}[5m]
                ) * 1024 * 1024
            ))""",
        "total": """sum by (cluster_domain) (
            max by (cluster_domain, ip) (
                max_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{instance_role="backend_master"}[5m]
                ) * 1024 * 1024
            ))""",
    },
    ClusterType.TenDBCluster: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            avg by (cluster_domain, ip) (
                avg_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_used_mb{instance_role="remote_master"}[1m]
                ) * 1024))""",
        "total": """sum by (cluster_domain) (
            avg by (cluster_domain, ip) (
                avg_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{instance_role="remote_master"}[1m]
                ) * 1024))""",
    },
    # es采集器本身存在容量统计指标（elasticsearch_filesystem_data_size_bytes、elasticsearch_indices_store_size_bytes）
    # 但数据节点只注册了一个，这里暂时用磁盘容量计算
    ClusterType.Es: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            sum_over_time(
                bkmonitor:dbm_system:disk:used{
                        device_type=~"ext.?|xfs",
                        instance_role=~"^(es_datanode_hot|es_datanode_cold)$",
                        mount_point!~"^(/|/usr/local)$"
                    }[1m]
                ))""",
        "total": """sum by (cluster_domain) (
            sum_over_time(
                bkmonitor:dbm_system:disk:total{
                        device_type=~"ext.?|xfs",
                        instance_role=~"^(es_datanode_hot|es_datanode_cold)$",
                        mount_point!~"^(/|/usr/local)$"
                    }[1m]
                ))""",
    },
    ClusterType.Kafka: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            sum_over_time(
                bkmonitor:dbm_system:disk:used{
                    device_type=~"ext.?|xfs",instance_role="broker",mount_point!~"^(/|/usr/local)$"
                }[1m]
            ))""",
        "total": """sum by (cluster_domain) (
            sum_over_time(
                bkmonitor:dbm_system:disk:total{
                    device_type=~"ext.?|xfs",
                    instance_role="broker",
                    mount_point!~"^(/|/usr/local)$"
                }[1m]
            ))""",
    },
    ClusterType.Pulsar: {
        "range": 5,
        "used": """sum by (cluster_domain) (
            sum_over_time(
                bkmonitor:dbm_system:disk:used{
                    device_type=~"ext.?|xfs",
                    instance_role="pulsar_bookkeeper",
                    mount_point!~"^(/|/usr/local)$"
                }[1m]
            ))""",
        "total": """sum by (cluster_domain) (
            sum_over_time(
                bkmonitor:dbm_system:disk:total{
                    device_type=~"ext.?|xfs",
                    instance_role="pulsar_bookkeeper",
                    mount_point!~"^(/|/usr/local)$"
                }[1m]
            ))""",
    },
    ClusterType.Hdfs: {
        "range": 5,
        "used": """avg by (cluster_domain) (
                    avg_over_time(bkmonitor:exporter_dbm_hdfs_exporter:hadoop_namenode_capacity_used[1m]))""",
        "total": """avg by (cluster_domain) (
                    avg_over_time(bkmonitor:exporter_dbm_hdfs_exporter:hadoop_namenode_capacity_total[1m]))""",
    },
    ClusterType.Influxdb: {
        "range": 5,
        "used": """max by (instance_host) (
            max_over_time(bkmonitor:pushgateway_dbm_influxdb_bkpull:disk_used{path=~"^/data|/data1$"}[1m]))""",
        "total": """max by (instance_host) (
            max_over_time(bkmonitor:pushgateway_dbm_influxdb_bkpull:disk_total{path=~"^/data|/data1$"}[1m]))""",
    },
    ClusterType.Dbmon: {
        "range": 5,
        "heartbeat": """
        avg by (target,bk_biz_id,app,bk_cloud_id, cluster_domain, cluster_type, instance_role)
        (avg_over_time(custom:dbm_report_channel:redis_dbmon_heart_beat{{cluster_domain="{cluster_domain}"}}[1m]))""",
    },
}
