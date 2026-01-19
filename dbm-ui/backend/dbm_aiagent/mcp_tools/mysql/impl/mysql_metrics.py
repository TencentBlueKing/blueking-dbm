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
import copy
import json
import logging
import time

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterType
from backend.utils.time import timezone2timestamp

logger = logging.getLogger("root")

# 查询模板
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
    "down_sample_range": "1m",
    # 取最新的几个周期，可以加速查询（如果指标数据不连续，则查不出数据）
    "type": "range",
}

DISK_USAGE = {
    ClusterType.TenDBSingle: {
        "range": 129,
        "used": """max by (cluster_domain, instance, mount_point) (
                max_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_used_mb{cluster_domain=~="%s",instance_role="orphan",%s}[5m]
                ) * 1024 * 1024
        )""",
        "total": """max by (cluster_domain, instance, mount_point) (
                max_over_time(
                    bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{cluster_domain=~="%s",instance_role="orphan",%s}[5m]
                ) * 1024 * 1024
        )""",
    },
    ClusterType.TenDBHA: {
        "range": 129,
        "used": """max by (cluster_domain, instance, mount_point) (
            max_over_time(
                bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_used_mb{cluster_domain=~="%s",instance_role="backend_master",%s}[124m]
            ) * 1024 * 1024
        )""",
        "total": """max by (cluster_domain, instance, mount_point) (
            max_over_time(
                bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{cluster_domain=~="%s",instance_role="backend_master",%s}[124m]
            ) * 1024 * 1024
        )""",
    },
    ClusterType.TenDBCluster: {
        "range": 129,
        "used": """sum by (cluster_domain) (
        avg by (cluster_domain, instance, mount_point) (
            avg_over_time(
                bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_du_used_mb{cluster_domain=~="%s",instance_role="remote_master",%s}[124m]
            ) * 1024 * 1024))""",
        "total": """sum by (cluster_domain) (
        avg by (cluster_domain, ip, mount_point) (
            avg_over_time(
                bkmonitor:exporter_dbm_mysqld_exporter:mysql_datadir_df_total_mb{cluster_domain=~="%s",instance_role="remote_master",%s}[124m]
            ) * 1024 * 1024))""",
    },
}

CPU_SUMMARY = {
    ClusterType.TenDBHA: {
        "max": """max by (cluster_domain,instance_role) (
    max_over_time(bkmonitor:dbm_system:cpu_summary:usage{cluster_domain=~"%s",instance_role=~"proxy|backend_master"}[1m]))
    """
    },
    ClusterType.TenDBCluster: {
        "max": """max by (cluster_domain,instance_role) (
        max_over_time(bkmonitor:dbm_system:cpu_summary:usage{cluster_domain=~"%s",instance_role=~"spider_master|remote_master"}[1m]))
        """
    },
}

QPS_SUMMARY = {
    ClusterType.TenDBHA: {
        "max": """max by (instance_role) (
        rate(bkmonitor:exporter_dbm_mysqld_exporter:mysql_global_status_questions{cluster_domain=~"%s",instance_role="backend_master"}[2m]))
        """
    },
    ClusterType.TenDBCluster: {
        "max": """sum by (instance_role) (
        rate(bkmonitor:exporter_dbm_mysqld_exporter:mysql_global_status_questions{cluster_domain=~"%s",instance_role="spider_master"}[2m]))
        """
    },
}

SLOW_COUNT = {
    ClusterType.TenDBHA: {
        "sum": """sum(
        increase(bkmonitor:exporter_dbm_mysqld_exporter:mysql_global_status_slow_queries{cluster_domain=~"%s",instance_role="backend_master"}[1m]))
        by (instance_role)
        """
    },
    ClusterType.TenDBCluster: {
        "sum": """sum(
        increase(bkmonitor:exporter_dbm_mysqld_exporter:mysql_global_status_slow_queries{cluster_domain=~"%s",instance_role=~"spider_master|remote_master"}[1m]))
        by (instance_role)
        """
    },
}

THREADS_RUNNING = {
    ClusterType.TenDBHA: {
        "max": """max(
        max_over_time(bkmonitor:exporter_dbm_mysqld_exporter:__default__:mysql_global_status_threads_running{cluster_domain=~"%s",instance_role=~"backend_master"}[1m]))
        by (instance_role)
    """
    },
    ClusterType.TenDBCluster: {
        "max": """max(
        max_over_time(bkmonitor:exporter_dbm_mysqld_exporter:__default__:mysql_global_status_threads_running{cluster_domain=~"%s",instance_role=~"spider_master|remote_master"}[1m]))
        by (instance_role)
    """
    },
}

CONNECTIONS = {
    ClusterType.TenDBHA: {
        "max": """max(
        max_over_time(bkmonitor:exporter_dbm_mysqld_exporter:__default__:mysql_global_status_threads_connected{cluster_domain=~"%s",instance_role=~"backend_master"}[1m]))
        by (backend_master)
    """
    },
    ClusterType.TenDBCluster: {
        "max": """max(
        max_over_time(bkmonitor:exporter_dbm_mysqld_exporter:__default__:mysql_global_status_threads_connected{cluster_domain=~"%s",instance_role=~"spider_master"}[1m]))
        by (instance_role,instance)
    """
    },
}

METRIC_TYPES = {
    "disk_usage": DISK_USAGE,
    "cpu_summary": CPU_SUMMARY,
    "qps_summary": QPS_SUMMARY,
    "slow_count": SLOW_COUNT,
    "connections": CONNECTIONS,
    "threads_running": THREADS_RUNNING,
}


def query_mysql_metrics(cluster_type, cluster_domain, start_time, end_time, metric_type):
    # 获取查询模板
    query_template = METRIC_TYPES.get(metric_type)
    query_template_db = query_template.get(cluster_type)
    if not query_template_db:
        raise ValueError("No query template for cluster type: %s and metric type: %s", cluster_type, metric_type)

    if end_time:
        end_time = timezone2timestamp(end_time)
    else:
        end_time = int(time.time())

    if start_time:
        start_time = timezone2timestamp(start_time)
    else:
        start_time = end_time - int(5) * 60
    if end_time - start_time > 30 * 60:
        raise ValueError("Query time range too large. limit 30 minutes")

    tmpl = query_template_db.get("max", "sum")
    query_string = tmpl % cluster_domain

    # 查询业务固定为DBA，查询时间取模板range
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["end_time"] = end_time
    params["start_time"] = start_time
    params["query_configs"][0]["promql"] = query_string
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID

    logger.info("query_mysql_metrics params: %s", json.dumps(params))
    # 查询exporter up指标
    resp = BKMonitorV3Api.unify_query(params)

    series = resp["series"]
    return series
