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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.dbm_aiagent.mcp_tools.redis.enums import (
    MetricsGroupBy,
    MetricsInstanceRole,
    MetricsOutputMode,
    MetricType,
)


class RedisMetricsInputSerializer(serializers.Serializer):
    """Input serializer for Redis metrics queries"""

    cluster_domain = serializers.CharField(
        help_text=_(
            "Redis cluster domain name. Use DB meta tools (redis_query_meta_list_redis_clusters) to "
            "resolve from bk_biz_id or biz_name if not provided."
        )
    )
    metric_type = serializers.ChoiceField(
        choices=MetricType.get_choices(),
        help_text=_(
            "Type of metric to query. Pick based on what you need: "
            "resource usage (cpu_usage, memory_usage, io_usage, disk_usage), "
            "throughput (connections, qps), "
            "or latency (host_latency, command_latency, latency_distribution). "
            "Values: cpu_usage (CPU %), memory_usage (Memory %), connections, qps, io_usage, disk_usage, "
            "host_latency (avg latency μs), command_latency (requires group_by=['cmd'], μs), "
            "latency_distribution (proxy only, requires group_by=['bucket'])."
        ),
    )
    start_time = serializers.DateTimeField(
        required=False,
        help_text=_(
            "Optional: Start time in ISO format (e.g., 2026-01-08T16:33:38+08:00). Defaults to 30 minutes ago."
        ),
    )
    end_time = serializers.DateTimeField(
        required=False,
        help_text=_("Optional: End time in ISO format (e.g., 2026-01-08T16:33:38+08:00). Defaults to now."),
    )
    mode = serializers.ChoiceField(
        choices=MetricsOutputMode.get_choices(),
        default=MetricsOutputMode.STATS.value,
        help_text=_(
            "Output mode. Use 'stats' (default) for most analysis tasks. "
            "'stats' returns only scalar statistics (min, max, avg, median, p95, cv, trend) - for summaries and comparisons. "
            "'overall' returns only aggregated time series data - for charts/visualization. "
            "'both' returns both series and statistics - when you need detailed analysis with time series. "
            "If mode != 'stats', keep max_len_datapoints <= 15 to avoid context length issues."
        ),
    )
    group_by = serializers.ListField(
        child=serializers.ChoiceField(choices=[dim.value for dim in MetricsGroupBy]),
        required=False,
        allow_null=True,
        help_text=_(
            "Result breakdown. None=cluster-level. Dimensions: "
            "cluster_domain, ip, instance, cmd (command_latency), bucket (latency_distribution). "
            "Examples: ['ip'], ['instance'], ['cmd'], ['bucket']. Independent of ip/port filters."
        ),
    )
    max_len_datapoints = serializers.IntegerField(
        default=100,
        help_text=_(
            "Optional: Maximum number of data points in time series, default=100. "
            "**Important**: This determines the time window/interval for PromQL queries, not just result size. "
            "Larger values = shorter time windows (intervals) with more data points per unit time. "
            "Smaller values = longer time windows (intervals) with fewer data points per unit time. "
            "If mode != 'stats', keep this <= 15 to avoid context length issues."
        ),
    )
    instance_role = serializers.ChoiceField(
        choices=MetricsInstanceRole.get_choices(),
        default=MetricsInstanceRole.MASTER.value,
        help_text=_(
            "Role of instances to query: "
            "'redis_master' (default) queries Redis master instances, "
            "'redis_slave' queries Redis replica instances, "
            "'proxy' queries proxy instances (predixy or twemproxy, auto-selected by cluster type). "
            "Note: latency_distribution requires proxy and is auto-set regardless of this parameter."
        ),
    )
    ip = serializers.CharField(
        required=False,
        allow_null=True,
        help_text=_(
            "Optional: Filter by specific IP address to narrow query scope. "
            "When provided alone: Query all instances on that machine (MACHINE level aggregation). "
            "When provided with port: Query single instance (INSTANCE level aggregation). "
            "Works independently of group_by - you can filter by IP but group results by instance."
        ),
    )
    port = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=_(
            "Optional: Filter by specific port for single instance query. "
            "Must be used together with ip parameter. "
            "Together with ip, narrows query to single instance (INSTANCE level aggregation). "
            "Never set port without ip."
        ),
    )
    mermaid_format = serializers.BooleanField(
        default=False,
        help_text=_(
            "When True and mode != 'stats', returns a 'mermaid_code' field with pre-formatted "
            "mermaid xychart-beta code for visualization. Only active when series data exists. "
            "Series data is removed from response when mermaid_code is generated. "
            "**IMPORTANT**: Output mermaid_code AS-IS without modification or regeneration."
        ),
    )


class RedisMetricsOutputSerializer(serializers.Serializer):
    """Output serializer for Redis metrics queries"""

    series = serializers.JSONField(
        required=False,
        help_text=_(
            "Aggregated time series data (present when mode='overall' or mode='both'). "
            "Format depends on filtering scope and group_by: "
            "instance={'ip-port': [[value, timestamp], ...]}, machine={'ip:port1': [...], 'ip-port2': [...]}, "
            "cluster={'cluster_domain': [...]} or with group_by='ip': cluster={'ip1': [...], 'ip2': [...]}"
        ),
    )
    statistics = serializers.JSONField(
        required=False,
        help_text=_(
            "Statistics (mode='stats' or 'both'). Scalar or per-key: min, max, avg, median, p95, cv, trend. "
            "Keys: cluster_domain (no group_by) or ip/instance/cmd/bucket when group_by set."
        ),
    )
    mermaid_code = serializers.CharField(
        required=False,
        help_text=_(
            "Pre-formatted mermaid xychart-beta code (present when mermaid_format=True and series data exists). "
            "This content must be outputted AS-IS."
        ),
    )
