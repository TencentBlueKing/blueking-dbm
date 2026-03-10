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

from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsGroupBy, MetricsInstanceRole, MetricsStatsType, MetricType


class RedisMetricsBaseInputSerializer(serializers.Serializer):
    """Shared fields for all Redis metrics queries"""

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
            "Smaller values = longer time windows (intervals) with fewer data points per unit time."
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


class RedisMetricsSeriesInputSerializer(RedisMetricsBaseInputSerializer):
    """Input serializer for Redis metrics series (time series) queries"""

    mermaid_format = serializers.BooleanField(
        default=False,
        help_text=_(
            "When True, returns a 'mermaid_code' field with pre-formatted "
            "mermaid xychart-beta code for visualization. Only active when series data exists. "
            "Series data is removed from response when mermaid_code is generated. "
            "**IMPORTANT**: Output mermaid_code AS-IS without modification or regeneration."
        ),
    )


class RedisMetricsStatsInputSerializer(RedisMetricsBaseInputSerializer):
    """Input serializer for Redis metrics stats (scalar statistics) queries"""

    stats_type = serializers.ChoiceField(
        choices=MetricsStatsType.get_choices(),
        default=MetricsStatsType.VERTICAL.value,
        help_text=_(
            "Type of statistical computation. "
            "'vertical' (default): aggregate across instances first (e.g., SUM for QPS, MAX for CPU), "
            "then compute temporal stats (min/max/avg/p95/trend over time). "
            "Answers 'what was the cluster peak total QPS?'. "
            "'horizontal': compute stats across instances at each time point "
            "(e.g., min/max/avg instance QPS per timestamp), then summarize. "
            "Answers 'what was the highest QPS any single instance had?'."
        ),
    )


class RedisMetricsSeriesOutputSerializer(serializers.Serializer):
    """Output serializer for Redis metrics series queries"""

    series = serializers.JSONField(
        required=False,
        help_text=_(
            "Aggregated time series data. "
            "Format depends on filtering scope and group_by: "
            "instance={'ip-port': [[value, timestamp], ...]}, machine={'ip:port1': [...], 'ip-port2': [...]}, "
            "cluster={'cluster_domain': [...]} or with group_by='ip': cluster={'ip1': [...], 'ip2': [...]}"
        ),
    )
    mermaid_code = serializers.CharField(
        required=False,
        help_text=_(
            "Pre-formatted mermaid xychart-beta code (present when mermaid_format=True and series data exists). "
            "This content must be outputted AS-IS."
        ),
    )


class RedisMetricsStatsOutputSerializer(serializers.Serializer):
    """Output serializer for Redis metrics stats queries"""

    statistics = serializers.JSONField(
        required=False,
        help_text=_(
            "Per-key statistics dict. Each key maps to a dict with: "
            "min, max, avg, median, p95, cv (coefficient of variation %), "
            "trend (slope per minute), trend_unit, latest (last datapoint value). "
            "Keys depend on group_by: cluster_domain (no group_by), ip, instance, cmd, or bucket. "
            "With stats_type='vertical': stats are temporal — the aggregated cluster series "
            "(e.g., SUM of all instances' QPS) is computed first, then min/max/avg/p95/trend "
            "are calculated over time. 'max' = peak total cluster value. "
            "With stats_type='horizontal': stats are cross-instance — min/max/avg/stddev across "
            "instances are computed at each time point, then summarized. "
            "'max' = highest value any single instance had at any time point."
        ),
    )
