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
from backend.dbm_aiagent.mcp_tools.common.impl.promql_query import PromQLMultiQueryBuilder, PromQLQueryBuilder

MYSQL_MCP_DB_READ = "mysql-mcp-readonly"
MYSQL_MCP_DB_WRITE = "mysql-mcp"

DISK_USED = {
    "default": PromQLQueryBuilder(
        metric_name="mysql_datadir_du_used_mb",
        group_by=["cluster_domain", "instance_role"],
        aggregation="max",
        range_function="avg",
        step="129m",
        filters=[],
    ),
    ClusterType.TenDBCluster: PromQLQueryBuilder(
        metric_name="mysql_datadir_du_used_mb",
        group_by=["cluster_domain"],
        aggregation="sum",
        range_function="avg",
        step="129m",
        filters=[{"label_name": "instance_role", "op": "match", "value": "remote_master"}],
    ),
}

DISK_TOTAL = {
    "default": PromQLQueryBuilder(
        metric_name="mysql_datadir_df_total_mb",
        group_by=["cluster_domain", "instance_role"],
        aggregation="max",
        range_function="avg",
        step="129m",
        filters=[],
    ),
    ClusterType.TenDBCluster: PromQLQueryBuilder(
        metric_name="mysql_datadir_df_total_mb",
        aggregation_outer="sum:cluster_domain",  # 外部聚合
        group_by=["cluster_domain", "ip", "mount_point"],
        aggregation="avg",
        range_function="avg",
        step="129m",
        filters=[{"label_name": "instance_role", "op": "match", "value": "remote_master"}],
    ),
}

DISK_USAGE = {
    "default": PromQLMultiQueryBuilder(
        queries={
            "used": DISK_USED["default"],
            "total": DISK_TOTAL["default"],
        },
        expression="{used} / {total}",
        step="129m",
    ),
    ClusterType.TenDBCluster: PromQLMultiQueryBuilder(
        queries={
            "used": DISK_USED[ClusterType.TenDBCluster],
            "total": DISK_TOTAL[ClusterType.TenDBCluster],
        },
        expression="{used} / {total}",
        step="129m",
    ),
}

CPU_SUMMARY = {
    "default": PromQLQueryBuilder(
        metric_name="cpu_summary:usage",
        group_by=["instance_role", "bk_target_ip"],
        aggregation="max",
        range_function="max",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "orphan"},
        ],
    ),
    ClusterType.TenDBHA: PromQLQueryBuilder(
        metric_name="cpu_summary:usage",
        group_by=["instance_role"],
        aggregation="max",
        range_function="max",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "proxy|backend_master"},
        ],
    ),
    ClusterType.TenDBCluster: PromQLQueryBuilder(
        metric_name="cpu_summary:usage",
        group_by=["instance_role"],
        aggregation="max",
        range_function="max",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "spider_master|remote_master"},
        ],
    ),
}

MEMORY_USAGE = {
    "default": PromQLQueryBuilder(
        metric_name="mem:pct_used",
        group_by=["instance_role", "instance_host"],  # 按实例角色和实例IP聚合
        aggregation="max",
        range_function="max",
        step="1m",
        filters=[],
    ),
}

QPS_SUMMARY = {
    "default": PromQLQueryBuilder(
        metric_name="mysql_global_status_questions",
        group_by=["instance_role", "bk_target_ip"],
        aggregation="max",
        range_function="rate",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "orphan"},
        ],
    ),
    ClusterType.TenDBHA: PromQLQueryBuilder(
        metric_name="mysql_global_status_questions",
        group_by=["instance_role"],
        aggregation="max",
        range_function="rate",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "backend_master"},
        ],
    ),
    ClusterType.TenDBCluster: PromQLQueryBuilder(
        metric_name="mysql_global_status_questions",
        group_by=["instance_role"],
        aggregation="max",
        range_function="rate",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "spider_master"},
        ],
    ),
}

SLOW_COUNT = {
    "default": PromQLQueryBuilder(
        metric_name="mysql_global_status_slow_queries",
        group_by=["instance_role"],
        aggregation="sum",
        range_function="increase",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "backend_master|orphan"},
        ],
    ),
    ClusterType.TenDBCluster: PromQLQueryBuilder(
        metric_name="mysql_global_status_slow_queries",
        group_by=["instance_role"],
        aggregation="sum",
        range_function="increase",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "spider_master"},
        ],
    ),
}

THREADS_RUNNING = {
    "default": PromQLQueryBuilder(
        metric_name="mysql_global_status_threads_running",
        group_by=["instance_role"],
        aggregation="max",
        range_function="max",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "backend_master|orphan"},
        ],
    ),
    ClusterType.TenDBCluster: PromQLQueryBuilder(
        metric_name="mysql_global_status_threads_running",
        group_by=["instance_role"],
        aggregation="max",
        range_function="max",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "spider_master|remote_master"},
        ],
    ),
}

CONNECTIONS = {
    "default": PromQLQueryBuilder(
        metric_name="mysql_global_status_threads_connected",
        group_by=["instance_role"],
        aggregation="max",
        range_function="max",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "backend_master|orphan"},
        ],
    ),
    ClusterType.TenDBCluster: PromQLQueryBuilder(
        metric_name="mysql_global_status_threads_connected",
        group_by=["instance_role", "instance"],  # 按 instance 分组
        aggregation="max",
        range_function="max",
        step="1m",
        filters=[
            {"label_name": "instance_role", "op": "match", "value": "spider_master|remote_master"},
        ],
    ),
}


SLAVE_DELAY = {
    "default": PromQLQueryBuilder(
        metric_name="mysql_slave_seconds_behind_master",
        group_by=["instance_role", "instance", "master_server_id"],
        aggregation="avg",
        range_function="avg",
        step="1m",
        filters=[],
    )
}


METRIC_TYPES = {
    "disk_usage": DISK_USAGE,
    "disk_used": DISK_USED,
    "disk_total": DISK_TOTAL,
    "cpu_summary": CPU_SUMMARY,
    "qps_summary": QPS_SUMMARY,
    "memory_usage": MEMORY_USAGE,
    "slow_count": SLOW_COUNT,
    "connections": CONNECTIONS,
    "threads_running": THREADS_RUNNING,
    "slave_delay": SLAVE_DELAY,
}
