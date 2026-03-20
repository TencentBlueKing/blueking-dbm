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
            "Redis cluster domain name (e.g. 'cache.myapp.bizname.db'). "
            "If unknown, call redis_query_meta_list_redis_clusters with bk_biz_id or biz_name to look it up."
        )
    )
    metric_type = serializers.ChoiceField(
        choices=MetricType.get_choices(),
        help_text=_(
            "Metric to query. Choose by category: "
            "[Resource] cpu_usage (CPU %), memory_usage (Memory %), io_usage (IO %), disk_usage (Disk %). "
            "[Throughput] connections (connection count), qps (operations/s) "
            "-- NOTE: prefer instance_role='proxy' for connections and qps to measure client-facing traffic. "
            "[Latency] host_latency (average latency in μs), "
            "command_latency (per-command latency in μs; group_by=['cmd'] is auto-added), "
            "latency_distribution (latency bucket breakdown; group_by=['bucket'] and instance_role='proxy' "
            "are auto-set). "
            "[Capacity] capacity (used/available/total memory in bytes)."
        ),
    )
    start_time = serializers.DateTimeField(
        required=False,
        help_text=_(
            "Start of the query time range in ISO 8601 format (e.g. '2026-01-08T16:33:38+08:00'). "
            "Default: 30 minutes ago."
        ),
    )
    end_time = serializers.DateTimeField(
        required=False,
        help_text=_(
            "End of the query time range in ISO 8601 format (e.g. '2026-01-08T16:33:38+08:00'). " "Default: now."
        ),
    )
    group_by = serializers.ListField(
        child=serializers.ChoiceField(choices=[dim.value for dim in MetricsGroupBy]),
        required=False,
        allow_null=True,
        help_text=_(
            "Dimensions to break results down by. Omit (or null) for cluster-level aggregate. "
            "Valid choices: "
            "'ip' -- one series per host machine; "
            "'instance' -- one series per ip:port; "
            "'bucket' -- one series per latency bucket (only for metric_type='latency_distribution'); "
            "'cluster_domain' -- one series per cluster (rarely needed). "
            "NOTE: do NOT pass 'cmd'; it is automatically included when metric_type='command_latency'. "
            "group_by is independent of ip/port filters -- you can filter by ip while grouping by instance."
        ),
    )
    max_len_datapoints = serializers.IntegerField(
        default=100,
        help_text=_(
            "Maximum number of data points returned per series. Default: 100. "
            "Also controls the sampling interval: larger value = finer time granularity, "
            "smaller value = coarser granularity with fewer points."
        ),
    )
    instance_role = serializers.ChoiceField(
        choices=MetricsInstanceRole.get_choices(),
        default=MetricsInstanceRole.MASTER.value,
        help_text=_(
            "Which instance role to query. Values: 'redis_master', 'redis_slave', 'proxy'. "
            "Recommendations: "
            "connections / qps -- use 'proxy' (measures client-facing traffic). "
            "cpu_usage / memory_usage / io_usage / disk_usage / capacity -- use 'redis_master' (default) "
            "or 'proxy'. "
            "host_latency / command_latency -- use 'redis_master' (default) or 'proxy'. "
            "latency_distribution -- always uses 'proxy' (auto-set; this field is ignored)."
        ),
    )
    ip = serializers.CharField(
        required=False,
        allow_null=True,
        help_text=_(
            "Filter by a specific IP address. "
            "ip alone: queries all instances on that machine (MACHINE-level aggregation). "
            "ip + port: queries a single instance (INSTANCE-level aggregation). "
            "Independent of group_by -- you can filter by ip while still grouping results by instance."
        ),
    )
    port = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=_(
            "Filter by a specific port to target a single instance. "
            "CONSTRAINT: must be used together with ip. Never set port without ip."
        ),
    )


class RedisMetricsSeriesInputSerializer(RedisMetricsBaseInputSerializer):
    """Input serializer for Redis metrics series (time series) queries"""

    mermaid_format = serializers.BooleanField(
        default=False,
        help_text=_(
            "Set True to receive a pre-rendered mermaid xychart-beta chart in the 'mermaid_code' response field. "
            "When mermaid_code is generated, the raw series data is omitted from the response. "
            "IMPORTANT: output the returned mermaid_code verbatim -- do NOT modify or regenerate it."
        ),
    )


class RedisMetricsStatsInputSerializer(RedisMetricsBaseInputSerializer):
    """Input serializer for Redis metrics stats (scalar statistics) queries"""

    stats_type = serializers.ChoiceField(
        choices=MetricsStatsType.get_choices(),
        default=MetricsStatsType.VERTICAL.value,
        help_text=_(
            "How to compute statistics. "
            "'vertical' (default): aggregates all instances into one cluster-wide series first, "
            "then computes min/max/avg/p95/trend over time. "
            "Use when asking 'what was the cluster-wide peak total QPS?' "
            "'horizontal': computes stats across instances at each time point, then summarizes. "
            "Use when asking 'which instance had the highest QPS?'"
        ),
    )


class RedisMetricsSeriesOutputSerializer(serializers.Serializer):
    """Output serializer for Redis metrics series queries"""

    series = serializers.JSONField(
        required=False,
        help_text=_(
            "Time series data as {key: [[value, unix_timestamp], ...]}. "
            "The key depends on scope: "
            "ip+port filter -> key is 'ip:port'; "
            "ip-only filter -> one key per instance on that machine ('ip:port1', 'ip:port2', ...); "
            "no filter -> key is cluster_domain, or group_by dimension values (ip, instance, bucket). "
            "Value units match the metric_type: % for usage metrics, count for connections, "
            "ops/s for qps, μs for latency, bytes for capacity."
        ),
    )
    mermaid_code = serializers.CharField(
        required=False,
        help_text=_(
            "Pre-rendered mermaid xychart-beta chart code. Present only when mermaid_format=True "
            "and series data exists. Render this directly in a mermaid code block -- do NOT modify it."
        ),
    )


class RedisMetricsStatsOutputSerializer(serializers.Serializer):
    """Output serializer for Redis metrics stats queries"""

    statistics = serializers.JSONField(
        required=False,
        help_text=_(
            "Dict keyed by group dimension (cluster_domain when no group_by, otherwise ip / instance / "
            "cmd / bucket). Each value is a dict containing: "
            "min -- minimum observed value; "
            "max -- maximum observed value; "
            "avg -- arithmetic mean; "
            "median -- 50th percentile; "
            "p95 -- 95th percentile; "
            "cv -- coefficient of variation in % (higher = more volatile); "
            "trend -- slope per minute (positive = increasing, negative = decreasing); "
            "trend_unit -- unit string for the trend value; "
            "latest -- most recent data point value of the series. "
            "With stats_type='vertical': these stats describe the aggregated cluster-wide series over time "
            "(e.g. max = peak total cluster QPS). "
            "With stats_type='horizontal': these stats describe the spread across instances "
            "(e.g. max = highest value any single instance reached)."
        ),
    )
