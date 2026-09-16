# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像报告生成 —— 定时任务入口（DispatchQueue 版本）。

设计要点 / 怎么做：
    - @register_periodic_task(每日 0 点)：唯一触发点；函数名 / 触发时机保持向后兼容；
    - 选集群 + 分桶 + task.submit 全部**内联**在 producer 函数体内，
      不再引入 ClusterPortraitDispatcher / ClusterPortraitSelector 等中间层；
    - **不做 init_record**：占位记录由 :meth:`ClusterPortraitGenerator.run` 在 worker 侧
      内部落，避免 producer / worker 双写；
    - 走独立 namespace ``cluster_portrait``（``PortraitQueue``），与 Redis LLM 检查
      的 ``ai`` namespace 物理隔离，独立限流 / 独立观测 / 独立扩容；
    - 错峰改用 ``dispatch.scheduling.spread(window)``，不再使用 ``calculate_countdown``；
    - 去重改用 ``IdempotenceMode.DEDUPE``（work_item_id 携日期），不再使用 ``cache.add``；
    - 覆盖 TenDBSingle / TenDBHA / TenDBCluster 三个 cluster_type（业务上都属"MySQL 画像"）。

边界：
    - 未启用 AI（``ENABLE_DBM_AI=False``）-> 直接 return；
    - Task 配置 ``enabled=False`` -> 直接 return；
    - report_from / report_to 必须是 **aware datetime**（:meth:`ClusterPortraitGenerator.run`
      硬约束）；本文件通过 ``timezone.make_aware`` 构造，item 里以 isoformat 序列化，
      worker 侧 ``datetime.fromisoformat`` 会自动恢复 tzinfo；
    - task.submit 返回 CAPACITY_REJECTED / UNAVAILABLE -> warning 日志，次日重试；
    - task.submit 返回 DUPLICATE -> 仅计数（预期行为，dedupe 起作用）。
"""
import logging
import math
from datetime import date, datetime
from datetime import time as dt_time
from datetime import timedelta
from typing import Any, Dict, List

from celery.schedules import crontab
from django.utils import timezone

from backend import env
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
from backend.db_periodic_task.dispatch.scheduling import spread
from backend.db_periodic_task.local_tasks.cluster_portrait_report.mysql_portrait_task import MysqlPortraitReportTask
from backend.db_periodic_task.local_tasks.register import register_periodic_task

logger = logging.getLogger("celery")

#: 画像覆盖的 cluster_type 集合；三者业务上都属"MySQL 画像"，共用同一个消费者 Task
_PORTRAIT_CLUSTER_TYPES: List[str] = [
    ClusterType.TenDBSingle.value,
    ClusterType.TenDBHA.value,
    ClusterType.TenDBCluster.value,
]


def _select_daily_clusters(
    schedule_date: date,
    ignore_cluster_domains: List[str],
    daily_shuffle_limit: int,
) -> List[Cluster]:
    """选出当日待画像的集群列表（内联的分桶轮转逻辑）。

    功能说明 / 怎么做：
        - filter: ``cluster_type in _PORTRAIT_CLUSTER_TYPES``；
        - exclude: ``immute_domain in ignore_cluster_domains``；
        - 若 ``daily_shuffle_limit > 0`` 且总数超过阈值，按
          ``(id + schedule_date.toordinal()) % bucket_count == today_bucket`` 分桶轮转；
        - 否则不分桶；按 ``id`` 升序返回全量（或按 limit 截断）。

    :param schedule_date: 调度日期（``timezone.localdate()``，用于分桶轮转键）
    :param ignore_cluster_domains: 域名黑名单（命中直接排除）
    :param daily_shuffle_limit: 灰度限流上限；``0`` 表示不分桶全量画像
    :return: 已排序的 ``Cluster`` 列表（可能为空）

    边界：
        - 总数 == 0 -> 返回空列表
        - ``daily_shuffle_limit`` >= 总数 -> 退化为全量当天画像（不分桶）
    """
    base_qs = Cluster.objects.filter(cluster_type__in=_PORTRAIT_CLUSTER_TYPES)
    if ignore_cluster_domains:
        base_qs = base_qs.exclude(immute_domain__in=ignore_cluster_domains)

    total_count: int = base_qs.count()
    if total_count == 0:
        logger.info("[portrait_producer] no cluster matched; skip dispatch schedule_date=%s", schedule_date)
        return []

    # 分桶策略：日期参与散列，同一集群在不同日期会落到不同桶，避免固定集合被永远跳过
    bucket_count: int = 0
    today_bucket: int = 0
    if daily_shuffle_limit and total_count > daily_shuffle_limit:
        bucket_count = math.ceil(total_count / daily_shuffle_limit)
        # toordinal(): 公历日序数，按天 +1，与旧 ClusterPortraitDispatcher 语义一致
        day_ord: int = schedule_date.toordinal()
        today_bucket = day_ord % bucket_count
        # 用 Python 侧过滤 (id + day_ord) % bucket_count；避免引入 DB 侧 F/Mod 表达式的复杂度，
        # 总数 <= 数万级时纯 Python 侧过滤性能足够（一次全量取 id 集，一次按分桶过滤）
        candidate_ids: List[int] = list(base_qs.order_by("id").values_list("id", flat=True))
        picked_ids: List[int] = [cid for cid in candidate_ids if (cid + day_ord) % bucket_count == today_bucket]
        clusters: List[Cluster] = list(Cluster.objects.filter(id__in=picked_ids).order_by("id"))
    else:
        clusters = list(base_qs.order_by("id"))
        if daily_shuffle_limit:
            clusters = clusters[:daily_shuffle_limit]

    logger.info(
        "[portrait_producer] select done: schedule_date=%s total=%d bucket_count=%d today_bucket=%d selected=%d",
        schedule_date,
        total_count,
        bucket_count,
        today_bucket,
        len(clusters),
    )
    return clusters


def _build_report_window(schedule_date: date, days_back: int) -> tuple:
    """构造画像时间窗（aware datetime，走 Django 当前时区）。

    :param schedule_date: 调度日期
    :param days_back: 回溯天数；1 = 昨天整天
    :return: ``(report_from, report_to)``；均为 aware datetime
    边界：
        - :meth:`ClusterPortraitGenerator.run` 对 datetime 有 **strict-timezone** 约束，
          必须携带 tzinfo；``timezone.make_aware`` 保证满足此契约；
        - report_to 使用 23:59:59 会丢失当天最后 1 秒的微秒粒度，但生成器仅将其
          格式化为 prompt 文本，不用作 ORM/SQL filter，接受该微小误差以保留人类可读性。
    """
    reference_day: date = schedule_date - timedelta(days=days_back)
    report_from: datetime = timezone.make_aware(datetime.combine(reference_day, dt_time(0, 0, 0)))
    report_to: datetime = timezone.make_aware(datetime.combine(reference_day, dt_time(23, 59, 59)))
    return report_from, report_to


@register_periodic_task(run_every=crontab(minute=0, hour=0))
def generate_mysql_cluster_portrait_report() -> None:
    """MySQL 集群画像 —— DispatchQueue 版本 producer 入口（每日 0 点触发）。

    执行流程：
        1) 校验 ``env.ENABLE_DBM_AI`` / task ``config.enabled``；
        2) 计算画像时间窗（默认昨天整天，aware datetime，满足 run 的时区硬约束）；
        3) 内联选集群 + 分桶（``_select_daily_clusters``）；
        4) 构造 dispatch item（**不做 init_record**，占位记录由 worker 侧 run() 内部落）；
        5) ``task.submit(items, ready_at=spread(window))`` 入队；
        6) 打印结构化汇总日志（selected / enqueued / duplicates / capacity_rejected）。

    :return: None（本函数只做副作用；celery beat 忽略返回值）

    边界 / 异常：
        - AI 未启用 -> warning 日志 return；
        - task.config.enabled=False -> info 日志 return；
        - 无候选集群 -> info 日志 return；
        - task.submit 抛异常 -> 冒泡（celery 侧会重跑；本任务次日 beat 也会自然重试）。
    """
    if not env.ENABLE_DBM_AI:
        logger.warning("[portrait_producer] AI not enabled (env.ENABLE_DBM_AI=False); skip")
        return

    task = MysqlPortraitReportTask()
    cfg = task.config
    if not cfg.enabled:
        logger.info("[portrait_producer] task disabled via DispatchTaskSettings; task_key=%s skip", task.task_key)
        return

    schedule_date: date = timezone.localdate()
    report_from, report_to = _build_report_window(schedule_date, cfg.report_window_days_back)

    clusters = _select_daily_clusters(
        schedule_date=schedule_date,
        ignore_cluster_domains=cfg.ignore_cluster_domains,
        daily_shuffle_limit=cfg.daily_shuffle_limit,
    )
    if not clusters:
        return

    # ---- 组装 dispatch item（不做 init_record，占位记录由 worker 侧 run() 内部落） ----
    schedule_date_iso: str = schedule_date.isoformat()
    report_from_iso: str = report_from.isoformat()  # 携带 tzinfo，形如 "2026-09-14T00:00:00+08:00"
    report_to_iso: str = report_to.isoformat()

    items: List[Dict[str, Any]] = [
        {
            "cluster_id": cluster.id,
            "cluster_domain": cluster.immute_domain,
            "schedule_date": schedule_date_iso,
            "report_from_iso": report_from_iso,
            "report_to_iso": report_to_iso,
        }
        for cluster in clusters
    ]

    # ---- 错峰入队：window>0 时用 spread 均摊；否则立即 ready ----
    window: int = max(0, int(cfg.dispatch_spread_window_seconds))
    ready_at = spread(window) if window > 0 else None
    outcomes = task.submit(items, ready_at=ready_at)

    # ---- 汇总 outcomes：ENQUEUED / DUPLICATE / CAPACITY_REJECTED / UNAVAILABLE / DEADLINE ----
    counts: Dict[str, int] = {}
    for outcome in outcomes:
        counts[outcome.outcome.value] = counts.get(outcome.outcome.value, 0) + 1

    enqueued: int = counts.get(DispatchOutcomeType.ENQUEUED.value, 0)
    duplicates: int = counts.get(DispatchOutcomeType.ENQUEUE_DUPLICATE.value, 0)
    capacity_rejected: int = counts.get(DispatchOutcomeType.ENQUEUE_CAPACITY_REJECTED.value, 0)
    unavailable: int = counts.get(DispatchOutcomeType.ENQUEUE_UNAVAILABLE.value, 0)
    deadline_expired: int = counts.get(DispatchOutcomeType.ENQUEUE_DEADLINE_EXPIRED.value, 0)

    if capacity_rejected or unavailable:
        logger.warning(
            "[portrait_producer] partial admission failure: capacity_rejected=%d unavailable=%d "
            "(next daily beat will retry)",
            capacity_rejected,
            unavailable,
        )

    logger.info(
        "[portrait_producer] dispatch done: task_key=%s schedule_date=%s total=%d "
        "enqueued=%d duplicates=%d capacity_rejected=%d unavailable=%d deadline_expired=%d "
        "window_seconds=%d",
        task.task_key,
        schedule_date,
        len(clusters),
        enqueued,
        duplicates,
        capacity_rejected,
        unavailable,
        deadline_expired,
        window,
    )
