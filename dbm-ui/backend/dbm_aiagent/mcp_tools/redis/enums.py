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
from enum import Enum


class MetricType(str, Enum):
    """
    Metric types supported by Redis monitoring.
    These are used as suffix of metric key in METRIC_REGISTRY.
    """

    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    CONNECTIONS = "connections"
    QPS = "qps"
    IO_USAGE = "io_usage"
    DISK_USAGE = "disk_usage"
    HOST_LATENCY = "host_latency"
    COMMAND_LATENCY = "command_latency"
    LATENCY_DISTRIBUTION = "latency_distribution"  # proxy only

    @staticmethod
    def get_choices() -> list:
        """Get list of valid metric type values for serializer choices"""
        return [metric.value for metric in MetricType]


class MetricsInstanceRole(str, Enum):
    """Defines the roles of machine instances"""

    PROXY = "proxy"
    MASTER = "redis_master"
    SLAVE = "redis_slave"

    @staticmethod
    def get_choices() -> list:
        """Get list of valid instance role values for serializer choices"""
        return [role.value for role in MetricsInstanceRole]


class MetricsOutputMode(str, Enum):
    """Output modes for metric query results"""

    OVERALL = "overall"  # Returns only aggregated time series data
    STATS = "stats"  # Returns only scalar statistics
    BOTH = "both"  # Returns both series and statistics

    @staticmethod
    def get_choices() -> list:
        """Get list of valid output mode values for serializer choices"""
        return [mode.value for mode in MetricsOutputMode]


class MetricsAggregationLevel(str, Enum):
    """Defines the level at which metrics are aggregated"""

    INSTANCE = "instance"  # ip:port level - single Redis instance
    MACHINE = "machine"  # ip level - all instances on one machine
    CLUSTER = "cluster"  # cluster-wide - all machines in cluster


class MetricsAggFunction(str, Enum):
    """Aggregation functions used"""

    MIN = "min"
    MAX = "max"
    AVG = "avg"
    SUM = "sum"
    STDDEV = "stddev"

    @staticmethod
    def get_choices() -> list:
        return [func.value for func in MetricsAggFunction]


class MetricsGroupBy(str, Enum):
    """Defines the dimension for grouping metric results"""

    IP = "ip"  # Group by IP address
    INSTANCE = "instance"  # Group by instance (ip:port)
    CMD = "cmd"  # Group by command (for latency metrics)
    CLUSTER_DOMAIN = "cluster_domain"  # Aggregate at cluster level
    BUCKET = "bucket"  # Group by latency distribution buckets (for latency distribution metrics)

    @staticmethod
    def get_choices() -> list:
        """Get list of valid group_by values for serializer choices"""
        return [None] + [dim.value for dim in MetricsGroupBy]
