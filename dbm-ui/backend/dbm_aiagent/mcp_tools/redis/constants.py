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
from backend.db_report.enums import MetaCheckSubType
from backend.db_report.enums.redis_sub_type import RedisCheckSubType
from backend.db_report.models import MetaCheckReport, RedisCheckReport
from backend.dbm_aiagent.mcp_tools.redis.enums import (
    BUCKET_DIMENSION,
    CAPACITY_TYPE_DIMENSION,
    CMD_DIMENSION,
    MOUNT_POINT_DIMENSION,
)
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsAggFunction as AggFunction
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsGroupBy, RedisReportSubtype

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

# Redis metrics: BKMonitor query guards and retry behavior
METRICS_MAX_QUERY_RANGE_SECONDS = 6 * 30 * 24 * 60 * 60
METRICS_END_TIME_MAX_FUTURE_SKEW_SECONDS = 300
# Fixed PromQL range-vector lookback (max_over_time/rate/...[Xs]). Must stay aligned with
# scrape cadence (~1m). Do NOT tie this to datapoint downsampling — enlarging it turns each
# point into a long-window peak and inflates avg/min/p95 over the series.
METRICS_PROMQL_LOOKBACK_SECONDS = 60
# Caps per-query datapoints for series queries only; stats queries are exempt because
# denser resolution improves statistical accuracy without inflating response size.
# The query engine auto-adjusts step/interval (not PromQL lookback) to fit.
# At max range (6 months) with this cap, step is ~1 point per 8.6 hours.
# Callers needing denser resolution should query shorter time ranges rather than raising this cap.
METRICS_MAX_DATAPOINTS_LIMIT = 500
METRICS_QUERY_MAX_ATTEMPTS = 3
METRICS_QUERY_RETRY_DELAY_SEC = 0.5

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

# Trend unit per metric key: slope is normalized to (metric unit)/minute
# Used to clarify what "trend" means in statistics output
TREND_UNIT_BY_METRIC_KEY = {
    # Redis backend metrics
    "redis_cpu_usage": "%/min",
    "redis_instance_cpu_usage": "%/min",
    "redis_memory_usage": "%/min",
    "redis_connections": "connections/min",
    "redis_qps": "qps/min",
    "redis_io_usage": "%/min",
    "redis_disk_usage": "%/min",
    "redis_host_latency": "μs/min",
    "redis_command_latency": "μs/min",
    # Predixy proxy metrics
    "predixy_cpu_usage": "%/min",
    "predixy_memory_usage": "%/min",
    "predixy_connections": "connections/min",
    "predixy_qps": "qps/min",
    "predixy_io_usage": "%/min",
    "predixy_disk_usage": "%/min",
    "predixy_host_latency": "μs/min",
    "predixy_command_latency": "μs/min",
    "predixy_latency_distribution": "requests/min",
    # Twemproxy proxy metrics
    "twemproxy_cpu_usage": "%/min",
    "twemproxy_instance_cpu_usage": "%/min",
    "twemproxy_memory_usage": "%/min",
    "twemproxy_connections": "connections/min",
    "twemproxy_qps": "qps/min",
    "twemproxy_io_usage": "%/min",
    "twemproxy_disk_usage": "%/min",
    "twemproxy_host_latency": "μs/min",
    "twemproxy_command_latency": "μs/min",
    "twemproxy_latency_distribution": "requests/min",
    # Capacity metrics
    "capacity_memory": "bytes/min",
    "capacity_disk": "bytes/min",
}

# Unified Metric Registry
# Format: "{component}_{metric_name}"
# component: redis, predixy, twemproxy
# metric_name: cpu, memory, connections, qps, avg_latency, latency_distribution
#
# Template placeholders:
# - {group_by}: Comma-separated dimensions for INNER query (cluster_domain + required_dimensions)
# - {filters}: Full label filters (e.g., 'cluster_domain=~"cluster1|cluster2",instance_role="redis_master",ip="1.2.3.4"')
# - {time_window}: Fixed PromQL lookback seconds (METRICS_PROMQL_LOOKBACK_SECONDS, e.g. "60").
#   Not the query step/interval; step is set separately on unify_query interval.
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
# - intrinsic_dimensions: List of IntrinsicDimension objects describing metric-specific breakdowns
#   (e.g. cmd, latency bucket, capacity used/total/available) that are ALWAYS applied internally and are
#   NOT user-selectable. NATURAL_LABEL dims are appended to the inner/outer "by" clauses; SYNTHESIZED dims
#   are produced by a dedicated builder via label_replace. They are composed into result keys by key_order.
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
    # Per Redis process CPU (% of one core): irate(user)+irate(sys). Distinct from host
    # redis_cpu_usage (dbm_system multi-core). Outer agg is max across instances.
    "redis_instance_cpu_usage": {
        "promql_template": (
            "max by ({group_by}) (("
            "irate("
            "bkmonitor:exporter_dbm_redis_exporter:redis_cpu_user_seconds_total{{"
            "{filters}"
            "}}[{time_window}s]"
            ") + "
            "irate("
            "bkmonitor:exporter_dbm_redis_exporter:redis_cpu_sys_seconds_total{{"
            "{filters}"
            "}}[{time_window}s]"
            ")) * 100)"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "redis_memory_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:mem:pct_used{{"
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
    "redis_qps": {
        "promql_template": (
            "sum by ({group_by}) ("
            "rate("
            "bkmonitor:exporter_dbm_redis_exporter:redis_commands_total{{"
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
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_redis_exporter:redis_commands_total{{"
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
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_redis_exporter:redis_commands_total{{"
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
        ],
        "intrinsic_dimensions": [CMD_DIMENSION],
        "required_dimensions": ["ip", "instance_port"],
    },
    "capacity_memory": {
        "is_capacity": True,
        "intrinsic_dimensions": [CAPACITY_TYPE_DIMENSION],
        "sub_metrics": {
            "used": "bkmonitor:exporter_dbm_redis_exporter:redis_memory_used_bytes{{{filters}}}",
            "total": "bkmonitor:exporter_dbm_redis_exporter:redis_config_maxmemory{{{filters}}}",
        },
        "aggregation": {
            "overall": AggFunction.SUM,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "capacity_disk": {
        "is_capacity": True,
        # capacity_type (used/total/available) + per physical mount_point breakdown -> used@<ip>@<mount_point>.
        "intrinsic_dimensions": [CAPACITY_TYPE_DIMENSION, MOUNT_POINT_DIMENSION],
        # df_*_mb is a filesystem-level metric: instances sharing a data-dir mount report identical
        # values. Deduplicate each physical disk once (max per cluster_domain,ip,mount_point) and keep
        # that granularity in the output, mirroring the db_monitor capacity policy; otherwise a shared
        # disk is multiplied by the number of co-located instances.
        "capacity_dedup": {"agg": AggFunction.MAX, "by": ["cluster_domain", "ip", "mount_point"]},
        "sub_metrics": {
            "used": "bkmonitor:exporter_dbm_redis_exporter:redis_datadir_df_used_mb{{{filters}}} * 1024 * 1024",
            "total": "bkmonitor:exporter_dbm_redis_exporter:redis_datadir_df_total_mb{{{filters}}} * 1024 * 1024",
        },
        "aggregation": {
            "overall": AggFunction.SUM,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    # Predixy proxy metrics
    "predixy_cpu_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:cpu_summary:usage{{"
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
    # Predixy has no process-level CPU exporter metric; instance_cpu_usage is unsupported
    # (callers should use predixy_cpu_usage / MetricType.CPU_USAGE for host multi-core CPU).
    "predixy_memory_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:mem:pct_used{{"
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
    "predixy_qps": {
        "promql_template": (
            "sum by ({group_by}) ("
            "rate("
            "bkmonitor:exporter_dbm_predixy_exporter:predixy_cluster_total_requests{{"
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
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_predixy_exporter:predixy_cmdstat_calls_total{{"
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
        "instance_filter_mode": "instance_label",
    },
    "predixy_command_latency": {
        "promql_template": "{a} / {b}",
        "promql_parts": {
            "a": (
                "rate("
                "bkmonitor:exporter_dbm_predixy_exporter:predixy_cmdstat_usec_total{{"
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_predixy_exporter:predixy_cmdstat_calls_total{{"
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
        ],
        "intrinsic_dimensions": [CMD_DIMENSION],
        "required_dimensions": ["ip", "instance_port"],
        "instance_filter_mode": "instance_label",
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
                "{filters}"
                ',le="{le_upper}"'
                "}}[{time_window}s]"
                "))"
            ),
            "lower_bucket": (
                "sum by ({group_by}) ("
                "rate("
                "bkmonitor:exporter_dbm_predixy_exporter:predixy_cmdstat_response_latency_bucket{{"
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
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "intrinsic_dimensions": [BUCKET_DIMENSION],
        "required_dimensions": ["ip"],  # Inner query needs ip dimension for per-IP bucket counts
    },
    # Twemproxy proxy metrics
    # Host multi-core CPU — same source as redis/predixy cpu_usage (cpu_summary).
    "twemproxy_cpu_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:cpu_summary:usage{{"
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
    # Per Twemproxy process CPU (%): irate(process_cpu)/100. Distinct from host
    # twemproxy_cpu_usage (cpu_summary). Outer agg is max across instances.
    "twemproxy_instance_cpu_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "irate("
            "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_process_cpu{{"
            "{filters}"
            "}}[{time_window}s]"
            ") / 100)"
        ),
        "aggregation": {
            "overall": AggFunction.MAX,
            "stats": [AggFunction.MIN, AggFunction.MAX, AggFunction.AVG, AggFunction.STDDEV],
        },
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP, MetricsGroupBy.INSTANCE],
        "required_dimensions": ["ip", "instance_port"],
    },
    "twemproxy_memory_usage": {
        "promql_template": (
            "max by ({group_by}) ("
            "max_over_time("
            "bkmonitor:dbm_system:mem:pct_used{{"
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
            "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_client_connections{{"
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
    "twemproxy_qps": {
        "promql_template": (
            "sum by ({group_by}) ("
            "rate("
            "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_calls_total{{"
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
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_calls_total{{"
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
        "instance_filter_mode": "instance_label",
    },
    "twemproxy_command_latency": {
        "promql_template": "{a} / {b}",
        "promql_parts": {
            "a": (
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_usec_total{{"
                "{filters}"
                "}}[{time_window}s]"
                ")"
            ),
            "b": (
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_calls_total{{"
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
        ],
        "intrinsic_dimensions": [CMD_DIMENSION],
        "required_dimensions": ["ip", "instance_port"],
        "instance_filter_mode": "instance_label",
    },
    "twemproxy_latency_distribution": {
        "buckets": LATENCY_DISTRIBUTION_BUCKETS,
        "promql_template": "{upper_bucket} - {lower_bucket}",
        "promql_parts": {
            "upper_bucket": (
                "sum by ({group_by}) ("
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_response_latency_bucket{{"
                "{filters}"
                ',le="{le_upper}"'
                "}}[{time_window}s]"
                "))"
            ),
            "lower_bucket": (
                "sum by ({group_by}) ("
                "rate("
                "bkmonitor:exporter_dbm_twemproxy_exporter:twemproxy_cmdstat_response_latency_bucket{{"
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
        "supported_group_by": [MetricsGroupBy.CLUSTER_DOMAIN, MetricsGroupBy.IP],
        "intrinsic_dimensions": [BUCKET_DIMENSION],
        "required_dimensions": ["ip"],  # Inner query needs ip dimension for per-IP bucket counts
    },
}


REPORT_SUBTYPE_MAP = {
    RedisReportSubtype.EXPORTER: RedisCheckSubType.Exporter,
    RedisReportSubtype.CLUSTER_CAPACITY_GROWTH_RISK: RedisCheckSubType.ClusterCapacityGrowthRisk,
    RedisReportSubtype.BACKEND_LOAD_SKEW: RedisCheckSubType.BackendLoadSkew,
    RedisReportSubtype.BACKEND_DATA_SKEW: RedisCheckSubType.BackendDataSkew,
    RedisReportSubtype.CONFIG_INCONSISTENT: RedisCheckSubType.ConfigInconsistent,
    RedisReportSubtype.AFFINITY_VIOLATION: MetaCheckSubType.AffinityViolation,
    RedisReportSubtype.ISOLATED_INSTANCE: MetaCheckSubType.AloneInstance,
    RedisReportSubtype.STATUS_ABNORMAL: MetaCheckSubType.StatusAbnormal,
    RedisReportSubtype.ENTRY_INCONSISTENT: MetaCheckSubType.EntryInconsistent,
}

# Different report types may use different models
REPORT_MODEL_MAP = {
    RedisReportSubtype.EXPORTER: RedisCheckReport,
    RedisReportSubtype.CLUSTER_CAPACITY_GROWTH_RISK: RedisCheckReport,
    RedisReportSubtype.BACKEND_LOAD_SKEW: RedisCheckReport,
    RedisReportSubtype.BACKEND_DATA_SKEW: RedisCheckReport,
    RedisReportSubtype.CONFIG_INCONSISTENT: RedisCheckReport,
    RedisReportSubtype.AFFINITY_VIOLATION: MetaCheckReport,
    RedisReportSubtype.ISOLATED_INSTANCE: MetaCheckReport,
    RedisReportSubtype.STATUS_ABNORMAL: MetaCheckReport,
    RedisReportSubtype.ENTRY_INCONSISTENT: MetaCheckReport,
}

# Subtypes that the MCP agent is allowed to create via add_report_record.
CREATABLE_REPORT_SUBTYPES = frozenset(
    {
        RedisReportSubtype.CLUSTER_CAPACITY_GROWTH_RISK,
        RedisReportSubtype.BACKEND_LOAD_SKEW,
        RedisReportSubtype.BACKEND_DATA_SKEW,
    }
)


def get_creatable_subtype_choices():
    """Choices for add_report_record subtype field."""
    return [(st.value, RedisReportSubtype.get_choice_label(st)) for st in CREATABLE_REPORT_SUBTYPES]
