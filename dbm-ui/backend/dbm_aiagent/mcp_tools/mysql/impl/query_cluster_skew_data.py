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
from typing import Optional, Union

from backend.db_meta.models import Cluster
from backend.db_report.models.cluster_skew_detection import ClusterSkewDetection

# 检测周期 5min，间隔超过 10min 视为新 episode
_EPISODE_GAP = timedelta(minutes=10)


def _to_date(value: Union[date, datetime]) -> date:
    return value.date() if isinstance(value, datetime) else value


def _to_float(value) -> Optional[float]:
    return float(value) if value is not None else None


def _to_table(columns: list[str], rows: list[list]) -> dict:
    return {"columns": columns, "rows": rows}


def _aggregate_episode_deviations(
    episode_times: list[datetime],
    time_nodes: dict[datetime, dict[str, float]],
) -> tuple[str, str]:
    """episode 内各节点偏离程度：hot 取最大正偏离，cold 取最大负偏离（绝对值最大）。"""
    hot_max: dict[str, float] = {}
    cold_min: dict[str, float] = {}
    for detect_time in episode_times:
        for node, pct_dev in time_nodes[detect_time].items():
            if pct_dev > 0:
                hot_max[node] = max(hot_max.get(node, pct_dev), pct_dev)
            elif pct_dev < 0:
                cold_min[node] = min(cold_min.get(node, pct_dev), pct_dev)

    hot_dev = ",".join(f"{node}:+{pct:.1f}" for node, pct in sorted(hot_max.items(), key=lambda x: -x[1]))
    cold_dev = ",".join(f"{node}:{pct:.1f}" for node, pct in sorted(cold_min.items(), key=lambda x: x[1]))
    return hot_dev, cold_dev


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
) -> tuple[str, Optional[str]]:
    """根据高于均值的节点集合是否随时间变化，判断 fixed / migrating。"""
    hot_sets = [hot for _, hot, _ in snapshots]
    if len(set(hot_sets)) == 1:
        return "fixed", None

    transitions: list[str] = []
    for i in range(1, len(snapshots)):
        if hot_sets[i] != hot_sets[i - 1]:
            t = snapshots[i][0].strftime("%H:%M")
            hot_str = ",".join(sorted(hot_sets[i]))
            transitions.append(f"{t}→{hot_str}")

    return "migrating", ",".join(transitions) if transitions else None


def _build_episodes(
    metric_role_snapshots: dict[tuple[str, str], dict[datetime, dict[str, float]]],
) -> list[list]:
    """将 (metric, role) 分组的检测快照聚合为 episode 行。"""
    episode_rows: list[list] = []

    for (metric, role), time_nodes in sorted(metric_role_snapshots.items()):
        snapshots = [
            (
                t,
                frozenset(node for node, pct in nodes.items() if pct > 0),
                frozenset(node for node, pct in nodes.items() if pct < 0),
            )
            for t, nodes in sorted(time_nodes.items())
        ]
        for episode in _split_episodes(snapshots):
            start = episode[0][0].strftime("%Y-%m-%d %H:%M")
            end = episode[-1][0].strftime("%Y-%m-%d %H:%M")
            episode_times = [snap[0] for snap in episode]
            hot_dev, cold_dev = _aggregate_episode_deviations(episode_times, time_nodes)
            pattern, transitions = _classify_hot_pattern(episode)
            episode_rows.append(
                [
                    metric,
                    role,
                    pattern,
                    start,
                    end,
                    hot_dev,
                    cold_dev,
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
    "hot_deviations",
    "cold_deviations",
    "transitions",
]


def query_cluster_skew_data(cluster_obj: Cluster, from_date: datetime, to_date: datetime) -> dict:
    """
    查询集群倾斜事件段，面向大模型报告生成。

    Gini 判定在写入侧完成；每条记录含节点相对均值的 pct_deviation。
    查询侧按 pct_deviation 正负区分 hot/cold，并在 hot_deviations/cold_deviations 中
    给出 episode 内各节点的最大偏离百分比（严重程度）。
    """
    rows = list(
        ClusterSkewDetection.objects.using("doris")
        .filter(
            cluster_domain=cluster_obj.immute_domain,
            dt__range=(_to_date(from_date), _to_date(to_date)),
        )
        .values("detect_time", "metric_name", "instance_role", "node", "pct_deviation")
        .order_by("metric_name", "instance_role", "detect_time", "node")
    )

    period = {"from": _to_date(from_date).isoformat(), "to": _to_date(to_date).isoformat()}
    empty_result = {
        "has_skew": False,
        "cluster": cluster_obj.immute_domain,
        "period": period,
        "episodes": _to_table(_EPISODE_COLUMNS, []),
    }
    if not rows:
        return empty_result

    # (metric, role) → detect_time → node → pct_deviation
    metric_role_snapshots: dict[tuple[str, str], dict[datetime, dict[str, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in rows:
        pct_dev = _to_float(row["pct_deviation"])
        if not pct_dev:
            continue

        key = (row["metric_name"], row["instance_role"])
        metric_role_snapshots[key][row["detect_time"]][row["node"]] = pct_dev

    episode_rows = _build_episodes(metric_role_snapshots)
    if not episode_rows:
        return empty_result

    return {
        "has_skew": True,
        "cluster": cluster_obj.immute_domain,
        "period": period,
        "episodes": _to_table(_EPISODE_COLUMNS, episode_rows),
    }
