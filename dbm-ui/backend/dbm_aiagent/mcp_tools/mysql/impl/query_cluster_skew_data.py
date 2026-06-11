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
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional, TypedDict, Union

from django.utils import timezone as django_timezone

from backend.db_meta.models import Cluster
from backend.db_report.models.cluster_skew_detection import ClusterSkewDetection
from backend.utils.time import trans_time_zone

# 检测周期 5min，间隔超过 10min 视为新 episode
_EPISODE_GAP = timedelta(minutes=10)

# 查询侧绝对值过滤（不影响 Doris 写入）；组均值或单节点 abs_dev 过低则忽略
_METRIC_SKEW_QUERY_THRESHOLDS: dict[str, dict[str, float]] = {
    "cpu_summary": {"min_group_mean": 10, "min_abs_deviation": 5},  # CPU 使用率 %
    "qps_summary": {"min_group_mean": 50, "min_abs_deviation": 30},  # QPS
    "connections": {"min_group_mean": 20, "min_abs_deviation": 10},  # 连接数
    "memory_usage": {"min_group_mean": 15, "min_abs_deviation": 5},  # 内存使用率 %
    "disk_used": {"min_group_mean": 10240, "min_abs_deviation": 5120},  # 磁盘已用 MB（10GB / 5GB）
}
_DEFAULT_QUERY_THRESHOLD = {"min_group_mean": 0, "min_abs_deviation": 0}


class _NodeSnapshot(TypedDict):
    value: float
    mean_value: float
    pct_deviation: float
    abs_deviation: float


def _ensure_aware(dt: datetime) -> datetime:
    if django_timezone.is_naive(dt):
        return django_timezone.make_aware(dt, django_timezone.get_current_timezone())
    return dt


def _to_zoned_datetime(value: datetime, time_zone: str) -> datetime:
    return trans_time_zone(_ensure_aware(value), time_zone)


def _format_detect_time(value: datetime, time_zone: str, fmt: str) -> str:
    return _to_zoned_datetime(value, time_zone).strftime(fmt)


def _to_date(value: Union[date, datetime], time_zone: str) -> date:
    if isinstance(value, datetime):
        return _to_zoned_datetime(value, time_zone).date()
    return value


def _to_float(value) -> Optional[float]:
    return float(value) if value is not None else None


def _to_table(columns: list[str], rows: list[list]) -> dict:
    return {"columns": columns, "rows": rows}


def _get_metric_threshold(metric: str) -> dict[str, float]:
    return _METRIC_SKEW_QUERY_THRESHOLDS.get(metric, _DEFAULT_QUERY_THRESHOLD)


def _passes_snapshot_threshold(metric: str, nodes: dict[str, _NodeSnapshot]) -> bool:
    if not nodes:
        return False
    group_mean = max(node["mean_value"] for node in nodes.values())
    return group_mean >= _get_metric_threshold(metric)["min_group_mean"]


def _passes_node_threshold(metric: str, snap: _NodeSnapshot) -> bool:
    return snap["abs_deviation"] >= _get_metric_threshold(metric)["min_abs_deviation"]


def _format_node_deviation(node: str, snap: _NodeSnapshot) -> str:
    sign = "+" if snap["pct_deviation"] > 0 else ""
    return (
        f"{node} value={snap['value']:.1f} mean={snap['mean_value']:.1f} "
        f"pct={sign}{snap['pct_deviation']:.1f}% abs_dev={snap['abs_deviation']:.1f}"
    )


def _aggregate_episode_deviations(
    metric: str,
    episode_times: list[datetime],
    time_nodes: dict[datetime, dict[str, _NodeSnapshot]],
) -> tuple[Optional[float], str, str]:
    """episode 内各节点偏离：取 abs_deviation 最大的一次快照作为代表。"""
    best_by_node: dict[str, _NodeSnapshot] = {}
    group_means: list[float] = []

    for detect_time in episode_times:
        nodes = time_nodes.get(detect_time, {})
        if nodes:
            group_means.append(max(node["mean_value"] for node in nodes.values()))
        for node, snap in nodes.items():
            if not _passes_node_threshold(metric, snap):
                continue
            prev = best_by_node.get(node)
            if prev is None or snap["abs_deviation"] > prev["abs_deviation"]:
                best_by_node[node] = snap

    hot_nodes = {node: snap for node, snap in best_by_node.items() if snap["pct_deviation"] > 0}
    cold_nodes = {node: snap for node, snap in best_by_node.items() if snap["pct_deviation"] < 0}

    hot_str = "; ".join(
        _format_node_deviation(node, snap)
        for node, snap in sorted(hot_nodes.items(), key=lambda x: -x[1]["abs_deviation"])
    )
    cold_str = "; ".join(
        _format_node_deviation(node, snap)
        for node, snap in sorted(cold_nodes.items(), key=lambda x: -x[1]["abs_deviation"])
    )
    group_mean = round(max(group_means), 1) if group_means else None
    return group_mean, hot_str, cold_str


def _split_episodes(
    snapshots: list[tuple[datetime, frozenset[str], frozenset[str]]],
) -> list[list[tuple[datetime, frozenset[str], frozenset[str]]]]:
    """按检测时间间隔切分 episode。"""
    if not snapshots:
        return []

    episodes: list[list[tuple[datetime, frozenset[str], frozenset[str]]]] = [[snapshots[0]]]
    for snapshot in snapshots[1:]:
        if snapshot[0] - episodes[-1][-1][0] > _EPISODE_GAP:
            episodes.append([snapshot])
        else:
            episodes[-1].append(snapshot)
    return episodes


def _classify_hot_pattern(
    snapshots: list[tuple[datetime, frozenset[str], frozenset[str]]],
    time_zone: str,
) -> tuple[str, Optional[str]]:
    """根据高于均值的节点集合是否随时间变化，判断 fixed / migrating。"""
    hot_sets = [hot for _, hot, _ in snapshots]
    if len(set(hot_sets)) == 1:
        return "fixed", None

    transitions: list[str] = []
    for i in range(1, len(snapshots)):
        if hot_sets[i] != hot_sets[i - 1]:
            t = _format_detect_time(snapshots[i][0], time_zone, "%H:%M")
            hot_str = ",".join(sorted(hot_sets[i]))
            transitions.append(f"{t}→{hot_str}")

    return "migrating", ",".join(transitions) if transitions else None


def _build_metric_snapshots(
    metric: str,
    time_nodes: dict[datetime, dict[str, _NodeSnapshot]],
) -> list[tuple[datetime, frozenset[str], frozenset[str]]]:
    snapshots: list[tuple[datetime, frozenset[str], frozenset[str]]] = []
    for detect_time, nodes in sorted(time_nodes.items()):
        if not _passes_snapshot_threshold(metric, nodes):
            continue
        hot = frozenset(
            node for node, snap in nodes.items() if snap["pct_deviation"] > 0 and _passes_node_threshold(metric, snap)
        )
        cold = frozenset(
            node for node, snap in nodes.items() if snap["pct_deviation"] < 0 and _passes_node_threshold(metric, snap)
        )
        if hot or cold:
            snapshots.append((detect_time, hot, cold))
    return snapshots


def _build_episodes(
    metric_role_snapshots: dict[tuple[str, str], dict[datetime, dict[str, _NodeSnapshot]]],
    time_zone: str,
) -> list[list]:
    """将 (metric, role) 分组的检测快照聚合为 episode 行。"""
    episode_rows: list[list] = []

    for (metric, role), time_nodes in sorted(metric_role_snapshots.items()):
        snapshots = _build_metric_snapshots(metric, time_nodes)
        for episode in _split_episodes(snapshots):
            episode_times = [snap[0] for snap in episode]
            group_mean, hot_nodes, cold_nodes = _aggregate_episode_deviations(metric, episode_times, time_nodes)
            if not hot_nodes and not cold_nodes:
                continue

            start = _format_detect_time(episode[0][0], time_zone, "%Y-%m-%d %H:%M")
            end = _format_detect_time(episode[-1][0], time_zone, "%Y-%m-%d %H:%M")
            pattern, transitions = _classify_hot_pattern(episode, time_zone)
            episode_rows.append(
                [
                    metric,
                    role,
                    pattern,
                    start,
                    end,
                    group_mean,
                    hot_nodes,
                    cold_nodes,
                    transitions,
                ]
            )

    return episode_rows


_EPISODE_COLUMNS = [
    "metric",
    "role",
    "pattern",
    "start",
    "end",
    "group_mean",
    "hot_nodes",
    "cold_nodes",
    "transitions",
]


def query_cluster_skew_data(cluster_obj: Cluster, from_date: datetime, to_date: datetime) -> dict:
    """
    查询集群倾斜事件段，面向大模型报告生成。

    Gini 判定在写入侧完成；查询侧按绝对值阈值过滤低影响倾斜，并输出 value/mean/pct/abs_dev。
    """
    tz = cluster_obj.time_zone
    rows = list(
        ClusterSkewDetection.objects.using("doris")
        .filter(
            cluster_domain=cluster_obj.immute_domain,
            dt__range=(_to_date(from_date, tz), _to_date(to_date, tz)),
        )
        .values(
            "detect_time",
            "metric_name",
            "instance_role",
            "node",
            "value",
            "mean_value",
            "pct_deviation",
            "abs_deviation",
        )
        .order_by("metric_name", "instance_role", "detect_time", "node")
    )

    period = {"from": _to_date(from_date, tz).isoformat(), "to": _to_date(to_date, tz).isoformat(), "time_zone": tz}
    empty_result = {
        "has_skew": False,
        "cluster": cluster_obj.immute_domain,
        "period": period,
        "episodes": _to_table(_EPISODE_COLUMNS, []),
    }
    if not rows:
        return empty_result

    # (metric, role) → detect_time → node → NodeSnapshot
    metric_role_snapshots: dict[tuple[str, str], dict[datetime, dict[str, _NodeSnapshot]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in rows:
        pct_dev = _to_float(row["pct_deviation"])
        if pct_dev is None or pct_dev == 0:
            continue

        key = (row["metric_name"], row["instance_role"])
        metric_role_snapshots[key][row["detect_time"]][row["node"]] = {
            "value": _to_float(row["value"]) or 0,
            "mean_value": _to_float(row["mean_value"]) or 0,
            "pct_deviation": pct_dev,
            "abs_deviation": _to_float(row["abs_deviation"]) or 0,
        }

    episode_rows = _build_episodes(metric_role_snapshots, tz)
    if not episode_rows:
        return empty_result

    return {
        "has_skew": True,
        "cluster": cluster_obj.immute_domain,
        "period": period,
        "episodes": _to_table(_EPISODE_COLUMNS, episode_rows),
    }
