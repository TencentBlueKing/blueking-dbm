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
from dataclasses import dataclass
from typing import List, Tuple

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class MetricType(StrStructuredEnum):
    """Metric types supported by Redis monitoring.

    Used as the suffix of metric key in METRIC_REGISTRY.
    """

    CPU_USAGE = EnumField("cpu_usage", "CPU usage (host / machine level)")
    CPU_USAGE_INSTANCE = EnumField("cpu_usage_instance", "CPU usage (process / instance level, in cores)")
    MEMORY_USAGE = EnumField("memory_usage", "Memory usage")
    CONNECTIONS = EnumField("connections", "Connections")
    QPS = EnumField("qps", "QPS")
    IO_USAGE = EnumField("io_usage", "IO usage")
    DISK_USAGE = EnumField("disk_usage", "Disk usage")
    HOST_LATENCY = EnumField("host_latency", "Host latency")
    COMMAND_LATENCY = EnumField("command_latency", "Command latency")
    LATENCY_DISTRIBUTION = EnumField("latency_distribution", "Latency distribution (proxy only)")
    CAPACITY = EnumField("capacity", "Capacity (used/available/total)")

    @classmethod
    def get_proxy_cluster_api_choices(cls) -> List[Tuple]:
        """Choices for cluster-level proxy MCP APIs (capacity is backend-only;
        cpu_usage_instance is currently backend-only since predixy/twemproxy exporters
        do not expose process-level CPU counters)."""

        excluded = {cls.CAPACITY.value, cls.CPU_USAGE_INSTANCE.value}
        return [c for c in cls.get_choices() if c[0] not in excluded]

    @classmethod
    def get_backend_cluster_api_choices(cls) -> List[Tuple]:
        """Choices for cluster-level master/slave MCP APIs (latency_distribution is proxy-only)."""

        return [c for c in cls.get_choices() if c[0] != cls.LATENCY_DISTRIBUTION.value]

    @classmethod
    def get_instance_api_choices(cls) -> List[Tuple]:
        """Choices for instance-scoped MCP APIs (host-level cpu/memory/io/disk unavailable at ip:port scope;
        cpu_usage_instance is exposed instead for process-level CPU)."""

        host_level = {cls.CPU_USAGE.value, cls.MEMORY_USAGE.value, cls.IO_USAGE.value, cls.DISK_USAGE.value}
        return [c for c in cls.get_choices() if c[0] not in host_level]


class MetricsInstanceRole(StrStructuredEnum):
    """Roles of machine instances."""

    PROXY = EnumField("proxy", "Proxy")
    MASTER = EnumField("redis_master", "Redis master")
    SLAVE = EnumField("redis_slave", "Redis slave")


class MetricsAggregationLevel(StrStructuredEnum):
    """Level at which metrics are aggregated."""

    INSTANCE = EnumField("instance", "Instance (ip:port)")
    MACHINE = EnumField("machine", "Machine (ip)")
    CLUSTER = EnumField("cluster", "Cluster (all machines)")


class MetricsAggFunction(StrStructuredEnum):
    """Aggregation functions used in metric queries."""

    MIN = EnumField("min", "Min")
    MAX = EnumField("max", "Max")
    AVG = EnumField("avg", "Avg")
    SUM = EnumField("sum", "Sum")
    STDDEV = EnumField("stddev", "Stddev")


class MetricsGroupBy(StrStructuredEnum):
    """User-selectable structural dimension for grouping metric results.

    Only the cluster-structure dimensions are user-facing here. Metric-specific
    breakdowns (command, latency bucket, capacity sub-type, ...) are modelled as
    internal "intrinsic dimensions" (see ``IntrinsicDimension``) and are applied
    automatically by the query service -- they are never user-selectable.
    """

    IP = EnumField("ip", "IP address")
    INSTANCE = EnumField("instance", "Instance (ip:port)")
    CLUSTER_DOMAIN = EnumField("cluster_domain", "Cluster domain")

    @classmethod
    def get_cluster_api_choices(cls) -> List[str]:
        """User-visible group_by values for cluster-level Redis metrics MCP APIs."""
        return [cls.IP.value, cls.INSTANCE.value, cls.CLUSTER_DOMAIN.value]

    @classmethod
    def get_machine_api_choices(cls) -> List[str]:
        """User-visible group_by values for machine-level APIs; cluster_domain omitted (scope fixes cluster)."""
        return [cls.IP.value, cls.INSTANCE.value]

    @classmethod
    def get_instance_api_choices(cls) -> List[str]:
        """User-visible group_by values for instance-level APIs; cluster_domain and ip omitted."""
        return [cls.INSTANCE.value]


class IntrinsicDimensionKind(StrStructuredEnum):
    """How an intrinsic dimension is realized in the PromQL query pipeline."""

    NATURAL_LABEL = EnumField("natural_label", "Real PromQL label, added to the by() clause")
    SYNTHESIZED = EnumField("synthesized", "Produced via label_replace by a dedicated query builder")


@dataclass(frozen=True)
class IntrinsicDimension:
    """A metric-specific breakdown applied internally (not a user-facing group_by).

    Attributes:
        promql_label: The PromQL label name carried on result series
            (e.g. "cmd", "bucket_label", "capacity_type").
        kind: NATURAL_LABEL dims are appended to the inner/outer ``by(...)`` clauses;
            SYNTHESIZED dims are emitted by a dedicated builder via ``label_replace``.
        key_order: Relative ordering when composing result keys (lower comes first).

    To add a new metric-specific dimension:
      1. Declare an ``IntrinsicDimension`` instance here.
      2. Attach it to the relevant ``METRIC_REGISTRY`` entry via ``intrinsic_dimensions``.
      3. For NATURAL_LABEL: ensure the source metric actually exposes that label.
         For SYNTHESIZED: ensure a builder emits it via ``label_replace``.
    """

    promql_label: str
    kind: IntrinsicDimensionKind
    key_order: int = 100


# Canonical intrinsic dimensions. Reference these from METRIC_REGISTRY entries.
#
# key_order controls placement in composed result keys. The scope identifier (ip / ip:port) is
# inserted by the query service at SCOPE_KEY_ORDER (50): dims with key_order < 50 precede the scope,
# dims with key_order > 50 follow it. So capacity_type/bucket/cmd lead the key, while mount_point
# trails the scope -> e.g. "used@<ip>@<mount_point>".
CMD_DIMENSION = IntrinsicDimension("cmd", IntrinsicDimensionKind.NATURAL_LABEL, key_order=20)
BUCKET_DIMENSION = IntrinsicDimension("bucket_label", IntrinsicDimensionKind.SYNTHESIZED, key_order=10)
CAPACITY_TYPE_DIMENSION = IntrinsicDimension("capacity_type", IntrinsicDimensionKind.SYNTHESIZED, key_order=5)
# Disk capacity is per physical mount; mount_point trails the scope so keys read used@<ip>@<mount_point>.
MOUNT_POINT_DIMENSION = IntrinsicDimension("mount_point", IntrinsicDimensionKind.NATURAL_LABEL, key_order=60)


class RedisReportSubtype(StrStructuredEnum):
    """Redis check report subtype choices used by MCP report tools. For mapping into db_report.SubType."""

    AFFINITY_VIOLATION = EnumField("affinity_violation", "Affinity violation")
    ISOLATED_INSTANCE = EnumField("isolated_instance", "Isolated instance")
    STATUS_ABNORMAL = EnumField("status_abnormal", "Status abnormal")
    # Unified conf check: role mismatch + predixy server fail/conf drift.
    CONFIG_INCONSISTENT = EnumField("config_inconsistent", "Config inconsistent")
    ENTRY_INCONSISTENT = EnumField("entry_inconsistent", "Entry inconsistent")
    EXPORTER = EnumField("exporter", "Exporter")

    # Agent check subtypes
    CLUSTER_CAPACITY_GROWTH_RISK = EnumField("cluster_capacity_growth_risk", "Cluster capacity growth risk")
    BACKEND_LOAD_SKEW = EnumField("backend_load_skew", "Backend load skew")
    BACKEND_DATA_SKEW = EnumField("backend_data_skew", "Backend data skew")
