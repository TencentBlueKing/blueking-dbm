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

from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsGroupBy, MetricsStatsType, MetricType

# Shown on metric_type where capacity is allowed, and on capacity-related response fields.
_CAPACITY_METRIC_USER_GUIDANCE = _(
    "For metric_type=capacity: total bytes are normally stable within a single query window; "
    "when describing current state, lean on `latest` together with used/available. "
    "If total (or its min/max over the window) differs from that steady baseline across the period, "
    "it usually reflects scale-out, scale-in, or topology changes rather than continuous drift."
)


class RedisMetricsTimeWindowSerializer(serializers.Serializer):
    """start/end window and datapoint cap — shared by all Redis metrics query scopes."""

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
    max_len_datapoints = serializers.IntegerField(
        default=100,
        help_text=_(
            "Maximum number of data points returned per series. Default: 100. "
            "Also controls the sampling interval: larger value = finer time granularity, "
            "smaller value = coarser granularity with fewer points."
        ),
    )
    include_meta = serializers.BooleanField(
        default=False,
        help_text=_(
            "When true, the response includes a 'meta' dict keyed by cluster_domain. "
            "Each entry contains the cluster_type and an 'entities' list of "
            "{key, instance_role} objects. Useful for cross-cluster or mixed-role queries."
        ),
    )


# ---------------------------------------------------------------------------
# Cluster scope: proxy vs backend (master/slave)
# ---------------------------------------------------------------------------

_GROUP_BY_HELP_CLUSTER = _(
    "Dimensions to break results down by. Omit (or null) for a cluster-wide aggregate. "
    "Choices: 'ip' (per host), 'instance' (per ip:port), "
    "'bucket' (latency buckets; for latency_distribution), "
    "'cluster_domain' (per cluster; rarely needed at cluster scope)."
)


class ClusterDomainsFieldMixin(serializers.Serializer):
    cluster_domains = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        max_length=50,
        required=True,
        help_text=_("Redis cluster domain names list."),
    )


class RedisMetricsClusterProxyInputSerializer(ClusterDomainsFieldMixin, RedisMetricsTimeWindowSerializer):
    """Cluster-level proxy queries: cluster_domain + proxy metric and group_by sets."""

    metric_type = serializers.ChoiceField(
        choices=MetricType.get_proxy_cluster_api_choices(),
        help_text=_(
            "Metric to query (proxy nodes; capacity is not available at proxy). "
            "[Resource] cpu_usage, memory_usage, io_usage, disk_usage. "
            "[Throughput] connections, qps. "
            "[Latency] host_latency, command_latency (group_by cmd is auto-added), "
            "latency_distribution (per bucket when grouped by bucket). "
        ),
    )
    group_by = serializers.ListField(
        child=serializers.ChoiceField(choices=MetricsGroupBy.get_cluster_api_choices()),
        required=False,
        allow_null=True,
        default=[MetricsGroupBy.CLUSTER_DOMAIN.value],
        help_text=_GROUP_BY_HELP_CLUSTER,
    )


class RedisMetricsClusterBackendInputSerializer(ClusterDomainsFieldMixin, RedisMetricsTimeWindowSerializer):
    """Cluster-level master/slave queries: cluster_domain + backend metric and group_by sets."""

    metric_type = serializers.ChoiceField(
        choices=MetricType.get_backend_cluster_api_choices(),
        help_text=_(
            "Metric to query (backend nodes; latency_distribution is proxy-only). "
            "[Resource] cpu_usage, memory_usage, io_usage, disk_usage. "
            "[Throughput] connections, qps. "
            "[Latency] host_latency, command_latency (group_by cmd is auto-added). "
            "[Capacity] capacity (used/available/total memory in bytes). "
        )
        + _CAPACITY_METRIC_USER_GUIDANCE,
    )
    group_by = serializers.ListField(
        child=serializers.ChoiceField(choices=MetricsGroupBy.get_cluster_api_choices()),
        required=False,
        allow_null=True,
        default=[MetricsGroupBy.CLUSTER_DOMAIN.value],
        help_text=_GROUP_BY_HELP_CLUSTER,
    )


# ---------------------------------------------------------------------------
# Machine scope
# ---------------------------------------------------------------------------


class RedisMetricsMachineInputSerializer(RedisMetricsTimeWindowSerializer):
    """Machine-level queries: ip + full metric_type + machine group_by."""

    ips = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        max_length=100,
        required=True,
        help_text=_("IP addresses of machines to query."),
    )
    metric_type = serializers.ChoiceField(
        choices=MetricType.get_choices(),
        help_text=_(
            "Metric to query. Role (proxy vs backend) is resolved from ip; "
            "latency_distribution is proxy-only, capacity is backend-only. "
            "[Resource] cpu_usage, memory_usage, io_usage, disk_usage. "
            "[Throughput] connections, qps. "
            "[Latency] host_latency, command_latency (group_by cmd is auto-added), latency_distribution. "
            "[Capacity] capacity. "
        )
        + _CAPACITY_METRIC_USER_GUIDANCE,
    )
    group_by = serializers.ListField(
        child=serializers.ChoiceField(choices=MetricsGroupBy.get_machine_api_choices()),
        required=False,
        allow_null=True,
        default=[MetricsGroupBy.IP.value],
        help_text=_(
            "Dimensions to break results down by. Default: ['ip']. Pass null for aggregate on this host. "
            "Choices: 'ip', 'instance' (ip:port on this machine), "
            "'bucket' (for latency_distribution). "
            "'cluster_domain' is not listed here — scope is already a single resolved cluster."
        ),
    )


class InstanceIdentifierSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("Instance IP"))
    port = serializers.IntegerField(help_text=_("Instance port"))


class RedisMetricsInstanceInputSerializer(RedisMetricsTimeWindowSerializer):
    """Instance-level queries: one or more ip:port + instance-safe metrics + instance group_by."""

    instances = InstanceIdentifierSerializer(
        many=True,
        required=True,
        help_text=_("Instance list with {ip, port}."),
    )
    metric_type = serializers.ChoiceField(
        choices=MetricType.get_instance_api_choices(),
        help_text=_(
            "Metric to query for a single ip:port. "
            "Host-level resource metrics (cpu_usage, memory_usage, io_usage, disk_usage) "
            "are not available at instance scope. "
            "latency_distribution is proxy-only; capacity is backend-only. "
            "[Throughput] connections, qps. "
            "[Latency] host_latency, command_latency (group_by cmd is auto-added), latency_distribution. "
            "[Capacity] capacity. "
        )
        + _CAPACITY_METRIC_USER_GUIDANCE,
    )
    group_by = serializers.ListField(
        child=serializers.ChoiceField(choices=MetricsGroupBy.get_instance_api_choices()),
        required=False,
        allow_null=True,
        default=[MetricsGroupBy.INSTANCE.value],
        help_text=_(
            "Dimensions to break results down by. Default: ['instance']. Pass null for aggregate on this instance. "
            "Choices: 'instance' (ip:port; same vocabulary as cluster APIs), "
            "'bucket' (for latency_distribution). "
            "'cluster_domain' and 'ip' are omitted — scope already fixes cluster and host."
        ),
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get("instances"):
            raise serializers.ValidationError(_("instances is required"))
        if len(attrs["instances"]) > 100:
            raise serializers.ValidationError(_("instances max length is 100"))
        return attrs


# ---------------------------------------------------------------------------
# Series / stats field mixins
# ---------------------------------------------------------------------------


class SeriesFieldMixin(serializers.Serializer):
    mermaid_format = serializers.BooleanField(
        default=False,
        help_text=_(
            "Set True to receive a pre-rendered mermaid xychart-beta chart in the 'mermaid_code' response field. "
            "When mermaid_code is generated, the raw series data is omitted from the response. "
            "IMPORTANT: output the returned mermaid_code verbatim -- do NOT modify or regenerate it."
        ),
    )


class StatsFieldMixin(serializers.Serializer):
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


# ---------------------------------------------------------------------------
# Concrete input serializers (scope x mode)
# ---------------------------------------------------------------------------


class RedisClusterProxySeriesInputSerializer(SeriesFieldMixin, RedisMetricsClusterProxyInputSerializer):
    pass


class RedisClusterProxyStatsInputSerializer(StatsFieldMixin, RedisMetricsClusterProxyInputSerializer):
    pass


class RedisClusterBackendSeriesInputSerializer(SeriesFieldMixin, RedisMetricsClusterBackendInputSerializer):
    pass


class RedisClusterBackendStatsInputSerializer(StatsFieldMixin, RedisMetricsClusterBackendInputSerializer):
    pass


class RedisMachineSeriesInputSerializer(SeriesFieldMixin, RedisMetricsMachineInputSerializer):
    pass


class RedisMachineStatsInputSerializer(StatsFieldMixin, RedisMetricsMachineInputSerializer):
    pass


class RedisInstanceSeriesInputSerializer(SeriesFieldMixin, RedisMetricsInstanceInputSerializer):
    pass


class RedisInstanceStatsInputSerializer(StatsFieldMixin, RedisMetricsInstanceInputSerializer):
    pass


# ---------------------------------------------------------------------------
# Output serializers (unchanged -- shared by all scopes)
# ---------------------------------------------------------------------------


class RedisMetricsSeriesOutputSerializer(serializers.Serializer):
    """Output serializer for Redis metrics series queries"""

    series = serializers.JSONField(
        required=False,
        help_text=_(
            "Time series data as {key: [[value, unix_timestamp], ...]}. "
            "The key depends on scope: "
            "instance scope -> key is 'ip:port'; "
            "machine scope -> one key per instance on that machine ('ip:port1', 'ip:port2', ...); "
            "cluster scope -> key is cluster_domain, or group_by dimension values (ip, instance, bucket). "
            "Value units match the metric_type: % for usage metrics, count for connections, "
            "ops/s for qps, μs for latency, bytes for capacity. "
            "For capacity, separate series correspond to used, available, and total. "
        )
        + _CAPACITY_METRIC_USER_GUIDANCE,
    )
    mermaid_code = serializers.CharField(
        required=False,
        help_text=_(
            "Pre-rendered mermaid xychart-beta chart code. Present only when mermaid_format=True "
            "and series data exists. Render this directly in a mermaid code block -- do NOT modify it."
        ),
    )
    partial_errors = serializers.JSONField(
        required=False,
        help_text=_("Optional per-cluster_type batch errors when partial data is returned."),
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
            "(e.g. max = highest value any single instance reached). "
            "For metric_type=capacity, keys distinguish used, available, and total. "
        )
        + _CAPACITY_METRIC_USER_GUIDANCE,
    )
    partial_errors = serializers.JSONField(
        required=False,
        help_text=_("Optional per-cluster_type batch errors when partial data is returned."),
    )
