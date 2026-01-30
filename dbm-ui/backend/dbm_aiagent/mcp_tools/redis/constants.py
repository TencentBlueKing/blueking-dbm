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
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsInstanceRole, MetricType

# Default query parameters for BKMonitor unify_query API
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
    "expression": "",
    "alias": "a",
    "start_time": 1697100405,
    "end_time": 1697101305,
    "slimit": 500,
    "down_sample_range": "",
    "type": "range",
}

# Unified query template - supports dynamic dimensions and aggregation functions
# {func} will be: max, sum, min, avg, etc.
# {dimensions} will be dynamically set based on aggregation level:
#   - cluster level: "cluster_domain"
#   - machine level: "cluster_domain,ip"
#   - instance level: "cluster_domain,ip,port"
PROMQL_TEMPLATE = (
    "{func} by ({dimensions}) "
    '({over_time}({data_source_key}{{cluster_domain=~"{cluster_domains}"{extra_labels}}}[{time_window}s]))'
)

TWEMPROXY_METRICS_KEY_MAP = {
    MetricType.CPU: "twemproxy_host_single_cpu",
    MetricType.MEMORY: "twemproxy_host_mem",
    MetricType.CONNECTIONS: "twemproxy_connections",
    MetricType.QPS: "twemproxy_qps",
}

PREDIXY_METRICS_KEY_MAP = {
    MetricType.CPU: "predixy_host_cpu",
    MetricType.MEMORY: "predixy_host_mem",
    MetricType.CONNECTIONS: "predixy_connections",
    MetricType.QPS: "predixy_qps",
}

REDIS_METRICS_KEY_MAP = {
    MetricType.CPU: "redis_host_cpu",
    MetricType.MEMORY: "redis_host_mem",
    MetricType.CONNECTIONS: "redis_connections",
    MetricType.QPS: "redis_qps",
}

# Unified metrics map for Redis backends and proxies
METRICS_CONFIG_MAP = {
    # Redis backend metrics
    "redis_host_cpu": {
        "data_source_key": "bkmonitor:dbm_system:cpu_summary:usage",
        "over_time": "max_over_time",
        "instance_role": MetricsInstanceRole.MASTER,
    },
    "redis_host_mem": {
        "data_source_key": "bkmonitor:dbm_system:mem:pct_used",
        "over_time": "max_over_time",
        "instance_role": MetricsInstanceRole.MASTER,
    },
    "redis_connections": {
        "data_source_key": "bkmonitor:exporter_dbm_redis_exporter:redis_connected_clients",
        "over_time": "max_over_time",
        "instance_role": MetricsInstanceRole.MASTER,
    },
    "redis_qps": {
        "data_source_key": "bkmonitor:exporter_dbm_redis_exporter:__default__:redis_commands_total",
        "over_time": "irate",
        "instance_role": MetricsInstanceRole.MASTER,
    },
    # Predixy proxy metrics
    "predixy_host_cpu": {
        "data_source_key": "bkmonitor:dbm_system:cpu_summary:usage",
        "over_time": "max_over_time",
        "instance_role": MetricsInstanceRole.PROXY,
    },
    "predixy_host_mem": {
        "data_source_key": "bkmonitor:dbm_system:mem:pct_used",
        "over_time": "max_over_time",
        "instance_role": MetricsInstanceRole.PROXY,
    },
    "predixy_connections": {
        "data_source_key": "bkmonitor:exporter_dbm_predixy_exporter:predixy_cluster_connections",
        "over_time": "max_over_time",
        "instance_role": MetricsInstanceRole.PROXY,
    },
    "predixy_qps": {
        "data_source_key": "bkmonitor:exporter_dbm_predixy_exporter:__default__:predixy_cluster_total_requests",
        "over_time": "irate",
        "instance_role": MetricsInstanceRole.PROXY,
    },
    # Twemproxy proxy metrics
    "twemproxy_host_single_cpu": {
        "data_source_key": "bkmonitor:dbm_system:cpu_detail:usage",
        "over_time": "max_over_time",
        "instance_role": MetricsInstanceRole.PROXY,
    },
    "twemproxy_host_mem": {
        "data_source_key": "bkmonitor:dbm_system:mem:pct_used",
        "over_time": "max_over_time",
        "instance_role": MetricsInstanceRole.PROXY,
    },
    "twemproxy_connections": {
        "data_source_key": "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_connections_curr",
        "over_time": "max_over_time",
        "instance_role": MetricsInstanceRole.PROXY,
    },
    "twemproxy_qps": {
        "data_source_key": "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_calls_total",
        "over_time": "irate",
        "instance_role": MetricsInstanceRole.PROXY,
    },
}
