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
import time
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import islice
from typing import Any, Generator, Iterable

import numpy as np
from blueapps.core.celery.celery import app
from django.core.cache import cache
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.local_tasks.mysql_cluster_skew.calculate_skew_data.fetch_metrics import (
    _fetch_key_metrics_of_cluster_instances,
)
from backend.db_report.models.cluster_skew_detection import ClusterSkewDetection

logger = logging.getLogger("celery.mysql_skew_detect.calculate_skew_data.skew_detect")


# 偏离详情字典结构，由 _detect_skew_by_gini 产出，贯穿 analyze → save 全流程
# DeviationDict = {
#     "node": "ip:port",           # 节点标识
#     "value": float,              # 该节点的实际指标值
#     "mean_value": float,         # 同组节点的均值
#     "pct_deviation": float,      # 相对偏离百分比 (value - mean) / mean * 100
#     "abs_deviation": float,      # 绝对偏离 |value - mean|
# }


def _analyze_cluster_skew(metrics_data: dict, gini_threshold: float = 0.2) -> dict[str, dict]:
    """对单个集群的指标数据做偏斜检测。

    按 role 分组后独立计算基尼系数，不同 role 的节点职责不同，混合比较无意义。

    Args:
        metrics_data: {
            metric_name: [
                {"ip": str, "port": str, "role": str, "avg": float, "cluster_domain": str},
                ...
            ]
        }

    Returns:
        {
            metric_name: {
                role: [DeviationDict, ...]
            }
        }
        无偏斜的 role 不出现在结果中。
        DeviationDict 结构见模块顶部定义。
    """
    results = {}
    for metric_name, instances in metrics_data.items():
        # 按 role 分组，同 role 的节点之间才比较偏斜
        groups = defaultdict(list)
        for inst in instances:
            groups[inst["role"]].append(inst)

        role_results = {}
        for role, role_instances in groups.items():
            node_names = [f"{inst['ip']}:{inst['port']}" for inst in role_instances]
            values = [inst["avg"] for inst in role_instances]
            deviations = _detect_skew_by_gini(values, node_names, gini_threshold)
            if deviations:
                role_results[role] = deviations

        results[metric_name] = role_results

    return results


def _detect_skew_by_gini(
    requests_per_node: list, node_names: list[str], gini_threshold: float
) -> list[dict[str, Any]]:
    """用基尼系数检测一组节点的负载偏斜。

    基尼系数范围 [0, 1)，0 表示完全均匀，越接近 1 越不均衡。
    超过阈值时返回同 role 下每个节点的偏离详情，按绝对偏离降序排列；未超过则返回空列表。

    Returns:
        [DeviationDict, ...] 按 abs_deviation 降序排列。
        DeviationDict 结构见模块顶部定义。
    """
    n = len(requests_per_node)
    if n <= 1:
        return []

    sorted_vals = np.sort(requests_per_node)
    cumx = np.cumsum(sorted_vals)
    # 基尼系数的离散形式计算
    if cumx[-1] == 0:
        gini = 0
    else:
        gini = (n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n

    if gini < gini_threshold:
        return []

    mean_val = np.mean(requests_per_node)
    deviations = []
    for node, req in zip(node_names, requests_per_node):
        if mean_val == 0:
            pct_dev = 0
        else:
            pct_dev = (req - mean_val) / mean_val * 100

        abs_dev = abs(req - mean_val)
        deviations.append(
            {
                "node": node,
                "value": req,
                "mean_value": round(float(mean_val), 2),
                "pct_deviation": round(pct_dev, 2),
                "abs_deviation": round(abs_dev, 2),
            }
        )

    deviations.sort(key=lambda x: -x["abs_deviation"])
    return deviations


def _batched(iterable: Iterable, n: int) -> Generator[list, None, None]:
    """将可迭代对象按固定大小分批产出，替代 Python 3.12+ 的 itertools.batched。"""
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch


def _detect_clusters_skew(
    cluster_type: ClusterType, cluster_domains: list[str], now: datetime
) -> tuple[dict[str, dict], float, float]:
    """批量获取指标并检测偏斜。

    一次 fetch 请求获取整批集群的指标（用 PromQL 正则匹配），然后按 cluster_domain 拆分后逐集群分析。

    Returns:
        (skew_results, fetch_elapsed, analyze_elapsed)
        skew_results: {
            cluster_domain: {
                metric_name: {
                    role: [DeviationDict, ...]
                }
            }
        }
        只包含存在偏斜的集群。DeviationDict 结构见模块顶部定义。
    """
    t_fetch = time.monotonic()
    metrics_data = _fetch_key_metrics_of_cluster_instances(
        cluster_type=cluster_type,
        cluster_domains=cluster_domains,
        end_time=now,
        time_window_len=timedelta(minutes=5),
    )
    fetch_elapsed = time.monotonic() - t_fetch

    t_analyze = time.monotonic()
    # 将批量返回的数据按 cluster_domain 拆分
    per_cluster = defaultdict(lambda: defaultdict(list))
    for metric_name, instances in metrics_data.items():
        for inst in instances:
            per_cluster[inst["cluster_domain"]][metric_name].append(inst)

    skew_results = {}
    no_metrics_count = 0
    for cluster_domain in cluster_domains:
        cluster_metrics = dict(per_cluster.get(cluster_domain, {}))
        if not cluster_metrics:
            no_metrics_count += 1
            logger.error("analyze failed, no metrics: cluster_domain=%s", cluster_domain)
            continue

        skew_result = _analyze_cluster_skew(cluster_metrics)
        if any(skew_result.values()):
            skew_results[cluster_domain] = skew_result
    analyze_elapsed = time.monotonic() - t_analyze

    logger.info(
        "analyze done: cluster_count=%d skew_count=%d no_metrics_count=%d elapsed=%.2fs",
        len(cluster_domains),
        len(skew_results),
        no_metrics_count,
        analyze_elapsed,
    )

    return skew_results, fetch_elapsed, analyze_elapsed


def _save_skew_records(skew_results: dict[str, dict], now: datetime) -> tuple[int, float]:
    """将偏斜检测结果组装为 ClusterSkewDetection 记录并批量写入 Doris。

    Args:
        skew_results: {
            cluster_domain: {
                metric_name: {
                    role: [DeviationDict, ...]
                }
            }
        }
        DeviationDict 结构见模块顶部定义。

    Returns:
        (写入记录数, 写入耗时秒数)
    """
    if not skew_results:
        logger.info("write skip, no skew results")
        return 0, 0.0

    dt = now.date()
    records = []
    for cluster_domain, skew_result in skew_results.items():
        for metric_name, role_deviations in skew_result.items():
            for instance_role, deviations in role_deviations.items():
                for d in deviations:
                    records.append(
                        ClusterSkewDetection(
                            dt=dt,
                            detect_time=now,
                            cluster_domain=cluster_domain,
                            metric_name=metric_name,
                            instance_role=instance_role,
                            node=d["node"],
                            value=round(d["value"], 2),
                            mean_value=d["mean_value"],
                            pct_deviation=d["pct_deviation"],
                            abs_deviation=d["abs_deviation"],
                        )
                    )

    t_write = time.monotonic()
    try:
        ClusterSkewDetection.objects.using("doris").bulk_create(records)
    except Exception:  # noqa
        logger.exception("write failed: record_count=%d skew_cluster_count=%d", len(records), len(skew_results))
        raise
    write_elapsed = time.monotonic() - t_write

    logger.info(
        "write done: record_count=%d skew_cluster_count=%d elapsed=%.2fs",
        len(records),
        len(skew_results),
        write_elapsed,
    )

    return len(records), write_elapsed


@app.task
def calculate_clusters_skew(cluster_type: str, cluster_domains: list[str], lock_key: str) -> None:
    """单批集群的完整处理流程：fetch → analyze → write，结束后记录各步耗时。"""

    logger.info(
        "batch start: cluster_type=%s lock_key=%s cluster_count=%d",
        cluster_type,
        lock_key,
        len(cluster_domains),
    )
    try:
        now = timezone.now().replace(tzinfo=None)
        skew_results, fetch_elapsed, analyze_elapsed = _detect_clusters_skew(
            ClusterType(cluster_type), cluster_domains, now
        )
        record_count, write_elapsed = _save_skew_records(skew_results, now)

        logger.info(
            "batch done: cluster_type=%s lock_key=%s cluster_count=%d skew_count=%d record_count=%d "
            "fetch=%.2fs analyze=%.2fs write=%.2fs",
            cluster_type,
            lock_key,
            len(cluster_domains),
            len(skew_results),
            record_count,
            fetch_elapsed,
            analyze_elapsed,
            write_elapsed,
        )
    except Exception:  # noqa
        logger.exception(
            "batch failed: cluster_type=%s lock_key=%s cluster_count=%d",
            cluster_type,
            lock_key,
            len(cluster_domains),
        )
        raise
    finally:
        if cache.get(lock_key) == 1:
            cache.delete(lock_key)
