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
import logging
import math
from datetime import datetime, timedelta
from typing import Optional, Tuple

from backend.db_services.redis.util import (
    is_predixy_proxy_type,
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
    is_twemproxy_proxy_type,
)
from backend.dbm_aiagent.mcp_tools.redis.constants import (
    METRIC_REGISTRY,
    METRICS_END_TIME_MAX_FUTURE_SKEW_SECONDS,
    METRICS_MAX_DATAPOINTS_LIMIT,
    METRICS_MAX_QUERY_RANGE_SECONDS,
)
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricsInstanceRole as InstanceRole
from backend.dbm_aiagent.mcp_tools.redis.enums import MetricType

logger = logging.getLogger("root")


def resolve_metric_key(
    cluster_type: str,
    metric_type: MetricType,
    instance_role: InstanceRole,
) -> Optional[str]:
    """
    Resolve metric key from METRIC_REGISTRY.

    Logic:
    1. Determine component (redis/predixy/twemproxy) from cluster_type and instance_role
    2. Determine metric name from metric_type
    3. Return "{component}_{metric_name}"

    Args:
        cluster_type: Cluster type string (e.g., "TendisTwemproxyRedisInstance")
        metric_type: Type of metric (MetricType enum)
        instance_role: Role of instances (InstanceRole enum)

    Returns:
        Metric key from METRIC_REGISTRY or None if not found
    """
    # Capacity metric uses cluster-type-based routing instead of component-based
    if metric_type == MetricType.CAPACITY:
        if is_redis_instance_type(cluster_type):
            metric_key = "capacity_memory"
        elif is_tendisssd_instance_type(cluster_type) or is_tendisplus_instance_type(cluster_type):
            metric_key = "capacity_disk"
        else:
            logger.warning(f"Cannot determine capacity type for cluster_type: {cluster_type}")
            return None
        return metric_key

    if instance_role == InstanceRole.PROXY:
        if is_twemproxy_proxy_type(cluster_type):
            component = "twemproxy"
        elif is_predixy_proxy_type(cluster_type):
            component = "predixy"
        else:
            logger.warning(f"Unknown proxy type for cluster_type: {cluster_type}")
            return None
    else:
        component = "redis"

    metric_key = f"{component}_{metric_type.value}"

    if metric_key not in METRIC_REGISTRY:
        logger.warning(f"Metric key '{metric_key}' not found in METRIC_REGISTRY")
        return None

    return metric_key


def explain_missing_metric_key(
    cluster_type: str,
    metric_type: MetricType,
    instance_role: InstanceRole,
) -> str:
    """Human-readable reason when resolve_metric_key returns None."""
    if (
        metric_type == MetricType.INSTANCE_CPU_USAGE
        and instance_role == InstanceRole.PROXY
        and is_predixy_proxy_type(cluster_type)
    ):
        return (
            "instance_cpu_usage is not available for Predixy proxy "
            "(no process-level CPU metric); use cpu_usage for host multi-core CPU instead"
        )
    return "No metric mapping found"


def calculate_time_range_window(
    max_len_datapoints: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    enforce_max_datapoints_limit: bool = True,
) -> Tuple[tuple, int]:
    """
    Calculate time range and window for metric queries.

    Args:
        max_len_datapoints: Maximum number of data points to return (0 = use default window only)
        start_time: Optional start time
        end_time: Optional end time
        enforce_max_datapoints_limit: When True (default), reject values above
            METRICS_MAX_DATAPOINTS_LIMIT.  Set to False for stats queries where
            denser resolution improves accuracy without inflating response size.

    Returns:
        Tuple of ((start_timestamp, end_timestamp), time_window_seconds)

    Raises:
        ValueError: If bounds are invalid, range exceeds METRICS_MAX_QUERY_RANGE_SECONDS, end is too far
        in the future, or max_len_datapoints is out of range.
    """
    time_window = 60  # Default interval in seconds

    if max_len_datapoints < 0:
        raise ValueError("max_len_datapoints must be non-negative")
    if enforce_max_datapoints_limit and max_len_datapoints > METRICS_MAX_DATAPOINTS_LIMIT:
        raise ValueError(f"max_len_datapoints cannot exceed {METRICS_MAX_DATAPOINTS_LIMIT}")

    def prepare_timestamp(is_start_time: bool, t: Optional[datetime]) -> int:
        if t:
            return int(t.timestamp())
        now = datetime.now()
        default_t = now - timedelta(minutes=30) if is_start_time else now
        return int(default_t.timestamp())

    start_ts = prepare_timestamp(True, start_time)
    end_ts = prepare_timestamp(False, end_time)

    if end_ts <= start_ts:
        raise ValueError("End time must be greater than start time")

    now_ts = int(datetime.now().timestamp())
    if end_ts > now_ts + METRICS_END_TIME_MAX_FUTURE_SKEW_SECONDS:
        raise ValueError(
            f"End time cannot be more than {METRICS_END_TIME_MAX_FUTURE_SKEW_SECONDS} seconds ahead of server time"
        )

    time_range_diff_sec = end_ts - start_ts
    if time_range_diff_sec > METRICS_MAX_QUERY_RANGE_SECONDS:
        raise ValueError(
            f"Query time range cannot exceed {METRICS_MAX_QUERY_RANGE_SECONDS // 86400} days "
            f"({METRICS_MAX_QUERY_RANGE_SECONDS} seconds)"
        )

    time_range = (start_ts, end_ts)

    if max_len_datapoints > 0:
        time_window = max(time_window, math.ceil(time_range_diff_sec / max_len_datapoints))

    return time_range, time_window
