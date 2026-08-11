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

from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsGroupBy, MetricType

# Shown on metric_type where capacity is allowed, and on capacity-related response fields.
_CAPACITY_METRIC_USER_GUIDANCE = _(
    "For metric_type=capacity: total bytes are normally stable within a single query window; "
    "when describing current state, lean on `latest` together with used/available. "
    "If total (or its min/max over the window) differs from that steady baseline across the period, "
    "it usually reflects scale-out, scale-in, or topology changes rather than continuous drift."
)

# Metric-specific breakdowns (per command, per latency bucket, capacity used/total/available) are applied
# automatically by the service and are NOT user-selectable group_by options.
_AUTOMATIC_BREAKDOWN_NOTE = _(
    "Metric-specific breakdowns are applied automatically and are not group_by options: "
    "command_latency is broken down per command; latency_distribution per latency bucket; "
    "capacity into used/available/total."
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

_GROUP_BY_HELP_CLUSTER = (
    _(
        "Dimensions to break results down by. Omit (or null) for a cluster-wide aggregate. "
        "Choices: 'ip' (per host), 'instance' (per ip:port), "
        "'cluster_domain' (per cluster; rarely needed at cluster scope). "
    )
    + _AUTOMATIC_BREAKDOWN_NOTE
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
            "Metric to query (proxy nodes; capacity and cpu_usage_instance are not available at proxy). "
            "[Resource] cpu_usage (machine-level, host CPU %), memory_usage, io_usage, disk_usage. "
            "[Throughput] connections, qps. "
            "[Latency] host_latency, command_latency (broken down per command automatically), "
            "latency_distribution (broken down per latency bucket automatically). "
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
            "[Resource] cpu_usage (machine-level, host CPU %), "
            "cpu_usage_instance (process-level, in cores, drill-down to ip:port), "
            "memory_usage, io_usage, disk_usage. "
            "[Throughput] connections, qps. "
            "[Latency] host_latency, command_latency (broken down per command automatically). "
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
            "latency_distribution is proxy-only; capacity and cpu_usage_instance are backend-only. "
            "[Resource] cpu_usage (machine-level, host CPU %), "
            "cpu_usage_instance (process-level, in cores, backend-only), "
            "memory_usage, io_usage, disk_usage. "
            "[Throughput] connections, qps. "
            "[Latency] host_latency, command_latency (broken down per command automatically), latency_distribution. "
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
            "Choices: 'ip', 'instance' (ip:port on this machine). "
            "'cluster_domain' is not listed here — scope is already a single resolved cluster. "
        )
        + _AUTOMATIC_BREAKDOWN_NOTE,
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
            "Machine-level resource metrics (cpu_usage, memory_usage, io_usage, disk_usage) "
            "are not available at instance scope -- use cpu_usage_instance for per-process CPU (backend-only, in cores). "
            "latency_distribution is proxy-only; capacity is backend-only. "
            "[Resource] cpu_usage_instance (process-level, in cores, backend-only). "
            "[Throughput] connections, qps. "
            "[Latency] host_latency, command_latency (broken down per command automatically), latency_distribution. "
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
            "Choices: 'instance' (ip:port; same vocabulary as cluster APIs). "
            "'cluster_domain' and 'ip' are omitted — scope already fixes cluster and host. "
        )
        + _AUTOMATIC_BREAKDOWN_NOTE,
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get("instances"):
            raise serializers.ValidationError(_("instances is required"))
        if len(attrs["instances"]) > 100:
            raise serializers.ValidationError(_("instances max length is 100"))
        return attrs


# ---------------------------------------------------------------------------
# Concrete input serializers (series vs stats share the same inputs)
# ---------------------------------------------------------------------------


class RedisClusterProxySeriesInputSerializer(RedisMetricsClusterProxyInputSerializer):
    pass


class RedisClusterProxyStatsInputSerializer(RedisMetricsClusterProxyInputSerializer):
    pass


class RedisClusterBackendSeriesInputSerializer(RedisMetricsClusterBackendInputSerializer):
    pass


class RedisClusterBackendStatsInputSerializer(RedisMetricsClusterBackendInputSerializer):
    pass


class RedisMachineSeriesInputSerializer(RedisMetricsMachineInputSerializer):
    pass


class RedisMachineStatsInputSerializer(RedisMetricsMachineInputSerializer):
    pass


class RedisInstanceSeriesInputSerializer(RedisMetricsInstanceInputSerializer):
    pass


class RedisInstanceStatsInputSerializer(RedisMetricsInstanceInputSerializer):
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
            "cluster scope -> key is cluster_domain, or group_by dimension values (ip, instance, and metric-specific fields). "
            "Value units match the metric_type: % for usage metrics, count for connections, "
            "ops/s for qps, μs for latency, bytes for capacity. "
            "For capacity, separate series correspond to used, available, and total. "
            "Disk-based capacity (e.g. Tendisplus/TendisSSD) is broken down per physical mount point. "
            "At cluster scope (default group_by or group_by=['cluster_domain']), keys look like "
            "'used@<mount_point>' with values summed across all hosts; at ip scope "
            "(group_by=['ip']), keys look like 'used@<ip>@<mount_point>'. Sum across mount-point "
            "series client-side for a host or cluster total. "
        )
        + _CAPACITY_METRIC_USER_GUIDANCE,
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
            "Dict keyed by group/breakdown dimension (cluster_domain when no group_by, otherwise ip / instance, "
            "plus automatic breakdowns: command for command_latency, latency bucket for latency_distribution). "
            "Each value is a dict of timeline statistics computed over the query window: "
            "min -- minimum observed value; "
            "max -- maximum observed value; "
            "avg -- arithmetic mean; "
            "median -- 50th percentile; "
            "p95 -- 95th percentile; "
            "cv -- coefficient of variation in % (higher = more volatile over time); "
            "trend -- slope per minute (positive = increasing, negative = decreasing); "
            "trend_unit -- unit string for the trend value; "
            "latest -- most recent data point value of the series. "
            "For metric_type=capacity, keys distinguish used, available, and total; disk-based capacity "
            "is further broken down per mount point. At cluster scope keys look like 'used@<mount_point>' "
            "(summed across hosts); at ip scope 'used@<ip>@<mount_point>'. "
        )
        + _CAPACITY_METRIC_USER_GUIDANCE,
    )
    partial_errors = serializers.JSONField(
        required=False,
        help_text=_("Optional per-cluster_type batch errors when partial data is returned."),
    )
