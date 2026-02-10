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
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsAggFunction as AggFunction
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsGroupBy

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

LATENCY_DISTRIBUTION_BUCKETS = [
    {"le_upper": "+Inf", "le_lower": "2.048e+06", "label": "(2s,+Inf]"},
    {"le_upper": "2.048e+06", "le_lower": "1.024e+06", "label": "(1s,2s]"},
    {"le_upper": "1.024e+06", "le_lower": "512000", "label": "(512ms,1s]"},
    {"le_upper": "512000", "le_lower": "256000", "label": "(256ms,512ms]"},
    {"le_upper": "256000", "le_lower": "128000", "label": "(128ms,256ms]"},
    {"le_upper": "128000", "le_lower": "64000", "label": "(64ms,128ms]"},
    {"le_upper": "64000", "le_lower": "32000", "label": "(32ms,64ms]"},
    {"le_upper": "32000", "le_lower": "16000", "label": "(16ms,32ms]"},
    {"le_upper": "16000", "le_lower": "8000", "label": "(8ms,16ms]"},
    {"le_upper": "8000", "le_lower": "4000", "label": "(4ms,8ms]"},
    {"le_upper": "4000", "le_lower": "", "label": "0ms,4ms]"},  # '(' causes promql parsing error, said bkmonitor api
]

# Unified Metric Registry
# Format: "{component}_{metric_name}"
# component: redis, predixy, twemproxy
# metric_name: cpu, memory, connections, qps, avg_latency, latency_distribution
#
# Template placeholders:
# - {group_by}: Comma-separated dimensions for INNER query (cluster_domain + required_dimensions)
# - {cluster_domains}: Regex pattern for cluster domains (e.g., "cluster1|cluster2")
# - {filters}: Additional label filters (e.g., ',instance_role="redis_master",ip="1.2.3.4"')
# - {time_window}: Time window in seconds (e.g., "60")
# - {overall_agg}: Aggregation function for overall mode (e.g., "max", "sum")
#   Stats queries use min/max/avg/stddev from the aggregation.stats list; no template placeholder.
#
# Configuration fields:
# - required_dimensions: List of dimensions that MUST be in the inner/base PromQL query's "by" clause.
#   These ensure the base query has the necessary granularity. Example: ["ip"] means the inner query
#   will always be "max by (cluster_domain, ip) (...)". These are NOT user-selectable.
#
# - supported_group_by: List of dimensions that users/LLMs can choose for the OUTER aggregation level.
#   These define what grouping options are available for the final results. Example: ["cluster_domain", "ip"]
#   means users can choose to aggregate at cluster level (group_by=None) or ip level (group_by=[MetricsGroupBy.IP]).
#   The outer query wraps the inner query: "max by (cluster_domain) (inner_query)" or
#   "max by (cluster_domain, ip) (inner_query)".
#
# Example for redis_cpu with required_dimensions=["ip"], supported_group_by=["cluster_domain", "ip"]:
#   Inner query (always): max by (cluster_domain, ip) (max_over_time(...))
#   Outer aggregation (user chooses):
#     - group_by=None: max by (cluster_domain) (inner_query) → cluster-level results
#     - group_by=[MetricsGroupBy.IP]: max by (cluster_domain, ip) (inner_query) → ip-level results
METRIC_REGISTRY = {
    # Redis backend metrics
    "redis_cpu_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:cpu_summary:usage{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],  # Inner query needs ip dimension for proper aggregation
    },
    "redis_memory_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:mem:pct_used{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],  # Inner query needs ip dimension for proper aggregation
    },
    "redis_connections": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:exporter_dbm_redis_exporter:redis_connected_clients{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "redis_qps": {
        "promql_template": (
            "sum by ({group_by}) ("
            "rate("
            "bkmonitor:exporter_dbm_redis_exporter:redis_commands_total{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.SUM,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "redis_io_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:io:util{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],
    },
    "redis_disk_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:disk:in_use{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],
    },
    "redis_host_latency": {
        # Host-level latency (microseconds): AVG aggregation across all commands
        "promql_template": "({a} * 1e6) / {b}",
        "promql_parts": {
            "a": (
                "rate("
                "bkmonitor:exporter_dbm_redis_exporter:redis_commands_duration_seconds_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_redis_exporter:redis_commands_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
        },
        "aggregation": {
            "overall": AggFunction.AVG,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "redis_command_latency": {
        "promql_template": "({a} * 1e6) / {b}",
        "promql_parts": {
            "a": (
                "rate("
                "bkmonitor:exporter_dbm_redis_exporter:redis_commands_duration_seconds_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_redis_exporter:redis_commands_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
        },
        "aggregation": {
            "overall": AggFunction.AVG,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [
            MetricsGroupBy.CLUSTER_DOMAIN,
            MetricsGroupBy.IP,
            MetricsGroupBy.INSTANCE,
            MetricsGroupBy.CMD,
        ],
        "required_dimensions": ["ip", "instance_port", "cmd"],
    },
    # Predixy proxy metrics
    "predixy_cpu_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:cpu_summary:usage{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],
    },
    "predixy_memory_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:mem:pct_used{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],
    },
    "predixy_connections": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:exporter_dbm_predixy_exporter:predixy_cluster_connections{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "predixy_qps": {
        "promql_template": (
            "sum by ({group_by}) ("
            "rate("
            "bkmonitor:exporter_dbm_predixy_exporter:predixy_cluster_total_requests{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.SUM,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "predixy_io_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:io:util{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],
    },
    "predixy_disk_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:disk:in_use{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],
    },
    "predixy_host_latency": {
        "promql_template": "{a} / {b}",
        "promql_parts": {
            "a": (
                "rate("
                "bkmonitor:exporter_dbm_predixy_exporter:predixy_cmdstat_usec_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_predixy_exporter:predixy_cmdstat_calls_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
        },
        "aggregation": {
            "overall": AggFunction.AVG,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "predixy_command_latency": {
        "promql_template": "{a} / {b}",
        "promql_parts": {
            "a": (
                "rate("
                "bkmonitor:exporter_dbm_predixy_exporter:predixy_cmdstat_usec_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_predixy_exporter:predixy_cmdstat_calls_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
        },
        "aggregation": {
            "overall": AggFunction.AVG,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [
            MetricsGroupBy.CLUSTER_DOMAIN,
            MetricsGroupBy.IP,
            MetricsGroupBy.INSTANCE,
            MetricsGroupBy.CMD,
        ],
        "required_dimensions": ["ip", "instance_port", "cmd"],
    },
    "predixy_latency_distribution": {
        # Bucket-based latency distribution
        "buckets": LATENCY_DISTRIBUTION_BUCKETS,
        "promql_template": "{upper_bucket} - {lower_bucket}",
        "promql_parts": {
            "upper_bucket": (
                "sum by ({group_by}) ("
                "rate("
                "bkmonitor:exporter_dbm_predixy_exporter:predixy_cmdstat_response_latency_bucket{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                ',le="{le_upper}"'
                "}}[{time_window}s]"
                "))"
            ),
            "lower_bucket": (
                "sum by ({group_by}) ("
                "rate("
                "bkmonitor:exporter_dbm_predixy_exporter:predixy_cmdstat_response_latency_bucket{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                ',le="{le_lower}"'
                "}}[{time_window}s]"
                "))"
            ),
        },
        "aggregation": {
            "overall": AggFunction.SUM,
            "stats": [AggFunction.MAX, AggFunction.MIN],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.BUCKET],
        "required_dimensions": ["ip"],  # Inner query needs ip dimension for per-IP bucket counts
    },
    # Twemproxy proxy metrics
    "twemproxy_cpu_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:cpu_detail:usage{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],  # Twemproxy uses cpu_detail which has device dimension
    },
    "twemproxy_memory_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:mem:pct_used{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],
    },
    "twemproxy_connections": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_connections_curr{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "twemproxy_qps": {
        "promql_template": (
            "sum by ({group_by}) ("
            "rate("
            "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_calls_total{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.SUM,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "twemproxy_io_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:io:util{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],
    },
    "twemproxy_disk_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:disk:in_use{{"
            'cluster_domain=~"{cluster_domains}"'
            "{filters}"
            "}}[{time_window}s]"
            "))"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "required_dimensions": ["ip"],
    },
    "twemproxy_host_latency": {
        "promql_template": "{a} / {b}",
        "promql_parts": {
            "a": (
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_usec_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_calls_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
        },
        "aggregation": {
            "overall": AggFunction.AVG,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "twemproxy_command_latency": {
        "promql_template": "{a} / {b}",
        "promql_parts": {
            "a": (
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_usec_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_calls_total{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
        },
        "aggregation": {
            "overall": AggFunction.AVG,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [
            MetricsGroupBy.CLUSTER_DOMAIN,
            MetricsGroupBy.IP,
            MetricsGroupBy.INSTANCE,
            MetricsGroupBy.CMD,
        ],
        "required_dimensions": ["ip", "instance_port", "cmd"],
    },
    "twemproxy_latency_distribution": {
        "buckets": LATENCY_DISTRIBUTION_BUCKETS,
        "promql_template": "{upper_bucket} - {lower_bucket}",
        "promql_parts": {
            "upper_bucket": (
                "sum by ({group_by}) ("
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_response_latency_bucket{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                ',le="{le_upper}"'
                "}}[{time_window}s]"
                "))"
            ),
            "lower_bucket": (
                "sum by ({group_by}) ("
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_response_latency_bucket{{"
                'cluster_domain=~"{cluster_domains}"'
                "{filters}"
                ',le="{le_lower}"'
                "}}[{time_window}s]"
                "))"
            ),
        },
        "aggregation": {
            "overall": AggFunction.SUM,
            "stats": [AggFunction.MAX, AggFunction.MIN],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.BUCKET],
        "required_dimensions": ["ip"],  # Inner query needs ip dimension for per-IP bucket counts
    },
}
