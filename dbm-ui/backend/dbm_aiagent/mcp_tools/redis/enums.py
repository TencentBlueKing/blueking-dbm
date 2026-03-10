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


class RedisReportSubtype(StrStructuredEnum):
    """Redis check report subtype choices used by MCP report tools."""

    AFFINITY_VIOLATION = EnumField("affinity_violation", "Affinity violation")
    ISOLATED_INSTANCE = EnumField("isolated_instance", "Isolated instance")
    STATUS_ABNORMAL = EnumField("status_abnormal", "Status abnormal")
    ROLE_MISMATCH = EnumField("role_mismatch", "Role mismatch")
    ENTRY_INCONSISTENT = EnumField("entry_inconsistent", "Entry inconsistent")
    EXPORTER = EnumField("exporter", "Exporter")

    # Agent check subtypes
    CLUSTER_MEMORY_CAPACITY_RISK = EnumField("cluster_memory_capacity_risk", "Cluster memory capacity risk")
    BACKEND_LOAD_SKEW = EnumField("backend_load_skew", "Backend load skew")
    BACKEND_DATA_SKEW = EnumField("backend_data_skew", "Backend data skew")
