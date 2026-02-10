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
from typing import Dict, List, Optional, Tuple

from backend.db_services.redis.util import is_predixy_proxy_type, is_twemproxy_proxy_type
from backend.dbm_aiagent.mcp_tools.redis.constants import METRIC_REGISTRY
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


def generate_mermaid_line_chart(
    title: str,
    series_data: Dict[str, List[List[float]]],
    y_label: str,
    y_min: Optional[float] = None,
    y_max: Optional[float] = None,
) -> str:
    """
    Generate mermaid xychart-beta line chart from time series data.
    Supports multiple series - each key in series_data becomes a separate line.

    Args:
        title: Chart title (e.g., "cluster.example.com CPU Usage")
        series_data: Dict with one or more keys, each containing [[value, timestamp], ...] data
                     Example: {"<ip>": [[50, 1706515200000], ...], "<ip>": [[45, 1706515200000], ...]}
        y_label: Y-axis label (e.g., "%CPU", "Memory %", "Connections")
        y_min: Optional minimum y-axis value (auto-calculated if None)
        y_max: Optional maximum y-axis value (auto-calculated if None)

    Returns:
        Formatted mermaid chart code ready to render
    """
    if not series_data:
        return ""

    # Collect all values and timestamps from all series
    all_values = []
    all_timestamps_set = set()
    series_by_key = {}

    for key, datapoints in series_data.items():
        if not datapoints:
            continue

        values = [point[0] for point in datapoints]
        timestamps = [point[1] for point in datapoints]

        all_values.extend(values)
        all_timestamps_set.update(timestamps)
        series_by_key[key] = {"values": values, "timestamps": timestamps}

    if not all_values or not all_timestamps_set:
        return ""

    # Use timestamps from first series for x-axis (assuming all series share same timestamps)
    first_key = list(series_by_key.keys())[0]
    reference_timestamps = series_by_key[first_key]["timestamps"]

    # Format timestamps based on time range
    time_range_hours = (reference_timestamps[-1] - reference_timestamps[0]) / 3600
    x_labels = _format_timestamps(reference_timestamps, time_range_hours)

    # Auto-calculate y-axis range if not provided
    if y_min is None:
        y_min = max(0, min(all_values) * 0.9)  # 10% padding below
    if y_max is None:
        y_max = max(all_values) * 1.1  # 10% padding above

    # Build mermaid code
    x_labels_string = ", ".join(f'"{label}"' for label in x_labels)
    mermaid_lines = [
        "```mermaid",
        "---",
        "config:",
        "  xyChart:",
        "    width: 1000",
        "    height: 700",
        "  themeVariables:",
        "    xyChart:",
        '      plotColorPalette: "#FF0000, #0000FF, #00FF00, #FFA500, #FF00FF, #00FFFF, #FFA07A, #98FB98"',
        "---",
        "xychart-beta",
        f'    title "{title}"',
        f"    x-axis [{x_labels_string}]",
        f'    y-axis "{y_label}" {y_min:.0f} --> {y_max:.0f}',
    ]

    # Add a line for each series
    for key, data in series_by_key.items():
        formatted_values = [f"{v:.2f}" for v in data["values"]]
        mermaid_lines.append(f'    line "{key}" [{", ".join(formatted_values)}]')

    mermaid_lines.append("```")

    return "\n".join(mermaid_lines)


def _format_timestamps(timestamps: List[int], time_range_hours: float) -> List[str]:
    """Format Unix timestamps for chart x-axis labels"""
    if not timestamps:
        return []
    datetimes = [datetime.fromtimestamp(ts) for ts in timestamps]

    # Strategy 1: Try HH:MM format
    hhmm_labels = [dt.strftime("%H:%M") for dt in datetimes]
    if len(hhmm_labels) == len(set(hhmm_labels)):
        # No duplicates - use compact HH:MM format
        return hhmm_labels

    # Strategy 2: Mark day boundaries
    dates = [dt.date() for dt in datetimes]
    unique_dates = set(dates)

    if len(unique_dates) == 1:
        # Single day with duplicate times (shouldn't happen, but fallback)
        return hhmm_labels

    # Strategy 3: Multiple days - mark first occurrence of each new day
    result = []
    prev_date = None

    for dt in datetimes:
        current_date = dt.date()

        if prev_date is None or current_date == prev_date:
            # Same day - use HH:MM
            result.append(dt.strftime("%H:%M"))
        else:
            # New day - use MM-DD HH:MM for first timestamp of new day
            result.append(dt.strftime("%m-%d %H:%M"))

        prev_date = current_date

    return result


def calculate_time_range_window(
    max_len_datapoints: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Tuple[tuple, int]:
    """
    Calculate time range and window for metric queries.

    Args:
        max_len_datapoints: Maximum number of data points to return
        start_time: Optional start time
        end_time: Optional end time

    Returns:
        Tuple of ((start_timestamp, end_timestamp), time_window_seconds)
    """
    time_window = 60  # Default interval in seconds

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

    time_range = (start_ts, end_ts)
    time_range_diff_sec = end_ts - start_ts

    if max_len_datapoints > 0:
        time_window = max(time_window, math.ceil(time_range_diff_sec / max_len_datapoints))

    return time_range, time_window
