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
from typing import List, Tuple

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class MetricType(StrStructuredEnum):
    """Metric types supported by Redis monitoring.

    Used as the suffix of metric key in METRIC_REGISTRY.
    """

    CPU_USAGE = EnumField("cpu_usage", "CPU usage")
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
        """Choices for cluster-level proxy MCP APIs (capacity is backend-only)."""

        return [c for c in cls.get_choices() if c[0] != cls.CAPACITY.value]

    @classmethod
    def get_backend_cluster_api_choices(cls) -> List[Tuple]:
        """Choices for cluster-level master/slave MCP APIs (latency_distribution is proxy-only)."""

        return [c for c in cls.get_choices() if c[0] != cls.LATENCY_DISTRIBUTION.value]

    @classmethod
    def get_instance_api_choices(cls) -> List[Tuple]:
        """Choices for instance-scoped MCP APIs (host resource metrics unavailable at ip:port scope)."""

        host_level = {cls.CPU_USAGE.value, cls.MEMORY_USAGE.value, cls.IO_USAGE.value, cls.DISK_USAGE.value}
        return [c for c in cls.get_choices() if c[0] not in host_level]


class MetricsInstanceRole(StrStructuredEnum):
    """Roles of machine instances."""

    PROXY = EnumField("proxy", "Proxy")
    MASTER = EnumField("redis_master", "Redis master")
    SLAVE = EnumField("redis_slave", "Redis slave")


class MetricsStatsType(StrStructuredEnum):
    """Type of statistical computation for metric results."""

    VERTICAL = EnumField("vertical", "Vertical (temporal stats on aggregated series)")
    HORIZONTAL = EnumField("horizontal", "Horizontal (stats across instances per time point)")


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
    """Dimension for grouping metric results."""

    IP = EnumField("ip", "IP address")
    INSTANCE = EnumField("instance", "Instance (ip:port)")
    CMD = EnumField("cmd", "Command")
    CLUSTER_DOMAIN = EnumField("cluster_domain", "Cluster domain")
    BUCKET = EnumField("bucket", "Latency bucket (distribution metrics only)")

    @classmethod
    def get_cluster_api_choices(cls) -> List[str]:
        """User-visible group_by values for cluster-level Redis metrics MCP APIs (CMD is service-injected)."""

        return [cls.IP.value, cls.INSTANCE.value, cls.BUCKET.value, cls.CLUSTER_DOMAIN.value]

    @classmethod
    def get_machine_api_choices(cls) -> List[str]:
        """User-visible group_by values for machine-level APIs; cluster_domain omitted (scope fixes cluster)."""

        return [cls.IP.value, cls.INSTANCE.value, cls.BUCKET.value]

    @classmethod
    def get_instance_api_choices(cls) -> List[str]:
        """User-visible group_by values for instance-level APIs; cluster_domain and ip omitted."""

        return [cls.INSTANCE.value, cls.BUCKET.value]


class RedisReportSubtype(StrStructuredEnum):
    """Redis check report subtype choices used by MCP report tools. For mapping into db_report.SubType."""

    AFFINITY_VIOLATION = EnumField("affinity_violation", "Affinity violation")
    ISOLATED_INSTANCE = EnumField("isolated_instance", "Isolated instance")
    STATUS_ABNORMAL = EnumField("status_abnormal", "Status abnormal")
    ROLE_MISMATCH = EnumField("role_mismatch", "Role mismatch")
    ENTRY_INCONSISTENT = EnumField("entry_inconsistent", "Entry inconsistent")
    EXPORTER = EnumField("exporter", "Exporter")

    # Agent check subtypes
    CLUSTER_CAPACITY_GROWTH_RISK = EnumField("cluster_capacity_growth_risk", "Cluster capacity growth risk")
    BACKEND_LOAD_SKEW = EnumField("backend_load_skew", "Backend load skew")
    BACKEND_DATA_SKEW = EnumField("backend_data_skew", "Backend data skew")
