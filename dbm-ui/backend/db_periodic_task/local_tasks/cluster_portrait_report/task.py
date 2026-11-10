# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像报告生成 —— 定时任务入口（DispatchQueue 版本，各 db_type 同批交错投递）。

设计要点 / 怎么做：
    - @register_periodic_task(每日 0 点)：唯一触发点 :func:`generate_cluster_portrait_report`，与 db_type 无关；
    - 参与投递的 Task = ``DISPATCH_REGISTRY`` 中所有 :class:`PortraitReportTaskBase` 子类；
      新 db_type 接入只需实现画像 Task + 配置（声明 ``task_key`` / ``default_cluster_types``），本文件无需改动；
    - 每个启用的画像 Task 按自身配置（``cluster_types`` / ``ignore_cluster_domains`` /
      ``daily_shuffle_limit`` / ``report_window_days_back``）独立选集群；
    - **交错投递**：``PortraitQueue`` pending 是按 ``ready_at`` 排序的 ZSET；各 Task 分别
      ``submit`` 时若各自取 ``time.time()``，先提交的 Task 会被整体排在前面。这里按注册顺序轮转
      （A0, B0, A1, B1, ...）给所有 item 分配全局序号，再由序号统一计算 ``ready_at``，
      使队列按 db_type 轮流出队；
    - **不做 init_record**：占位记录由 :meth:`ClusterPortraitGenerator.run` 在 worker 侧内部落；
    - 去重走 ``IdempotenceMode.DEDUPE``（work_item_id 携日期）。

边界：
    - 未启用 AI（``ENABLE_DBM_AI=False``）-> 直接 return；
    - Task 配置 ``enabled=False`` -> 该 Task 不参与本次投递；全部未启用 -> 直接 return；
    - report_from / report_to 必须是 **aware datetime**（:meth:`ClusterPortraitGenerator.run`
      硬约束）；本文件通过 ``timezone.make_aware`` 构造，item 里以 isoformat 序列化；
    - 单个 Task 加载配置 / 选集群 / submit 异常只记录日志，不影响其他 Task 投递；
    - task.submit 返回 CAPACITY_REJECTED / UNAVAILABLE -> warning 日志，次日重试；
    - task.submit 返回 DUPLICATE -> 仅计数（预期行为，dedupe 起作用）。
"""
import logging
import math
import time
from datetime import date, datetime
from datetime import time as dt_time
from datetime import timedelta
from typing import Any, Dict, List, Tuple, Type

from celery.schedules import crontab
from django.utils import timezone

from backend import env
from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models import Cluster
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY
from backend.db_periodic_task.local_tasks.cluster_portrait_report.base_portrait_task import PortraitReportTaskBase
from backend.db_periodic_task.local_tasks.register import register_periodic_task

logger = logging.getLogger("celery")

#: 窗口为 0 时相邻 item 的 ``ready_at`` 间隔（秒）；仅用于保持 ZSET 内的轮转顺序
_ZERO_WINDOW_STEP_SECONDS: float = 1e-3


def _select_daily_clusters(
    schedule_date: date,
    cluster_types: List[str],
    ignore_cluster_domains: List[str],
    daily_shuffle_limit: int,
) -> List[Cluster]:
    """选出当日待画像的集群列表（内联的分桶轮转逻辑）。

    功能说明 / 怎么做：
        - filter: ``cluster_type in cluster_types`` 且 ``phase=online``；
        - exclude: ``immute_domain in ignore_cluster_domains``；
        - 若 ``daily_shuffle_limit > 0`` 且总数超过阈值，按
          ``(id + schedule_date.toordinal()) % bucket_count == 0`` 分桶轮转；
        - 否则不分桶；按 ``id`` 升序返回全量（或按 limit 截断）。

    :param schedule_date: 调度日期（``timezone.localdate()``，用于分桶轮转键）
    :param cluster_types: 生效的 cluster_type 列表（已由配置解析出默认值）
    :param ignore_cluster_domains: 域名黑名单（命中直接排除）
    :param daily_shuffle_limit: 灰度限流上限；``0`` 表示不分桶全量画像
    :return: 已排序的 ``Cluster`` 列表（可能为空）

    边界：
        - 总数 == 0 -> 返回空列表
        - ``daily_shuffle_limit`` >= 总数 -> 退化为全量当天画像（不分桶）
    """
    base_qs = Cluster.objects.filter(cluster_type__in=cluster_types, phase=ClusterPhase.ONLINE.value)
    if ignore_cluster_domains:
        base_qs = base_qs.exclude(immute_domain__in=ignore_cluster_domains)

    total_count: int = base_qs.count()
    if total_count == 0:
        logger.info(
            "[portrait_producer] no cluster matched; skip dispatch schedule_date=%s cluster_types=%s",
            schedule_date,
            cluster_types,
        )
        return []

    # 分桶策略：日期参与散列，同一集群在不同日期会落到不同桶，避免固定集合被永远跳过
    bucket_count: int = 0
    today_bucket: int = 0
    if daily_shuffle_limit and total_count > daily_shuffle_limit:
        bucket_count = math.ceil(total_count / daily_shuffle_limit)
        # (id + day_ord) % bucket_count == 0：桶号随日期逐日轮转，bucket_count 天内覆盖全部集群
        today_bucket = (-schedule_date.toordinal()) % bucket_count
        candidate_ids: List[int] = list(base_qs.order_by("id").values_list("id", flat=True))
        picked_ids: List[int] = [cid for cid in candidate_ids if cid % bucket_count == today_bucket]
        clusters: List[Cluster] = list(Cluster.objects.filter(id__in=picked_ids).order_by("id"))
    else:
        clusters = list(base_qs.order_by("id"))
        if daily_shuffle_limit:
            clusters = clusters[:daily_shuffle_limit]

    logger.info(
        "[portrait_producer] select done: schedule_date=%s cluster_types=%s total=%d bucket_count=%d "
        "today_bucket=%d selected=%d",
        schedule_date,
        cluster_types,
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


def _build_items(task: PortraitReportTaskBase, schedule_date: date) -> List[Dict[str, Any]]:
    """按 Task 自身配置选集群并组装 dispatch items；Task 未启用或无候选集群时返回空列表。"""
    cfg = task.config
    if not cfg.enabled:
        logger.info("[portrait_producer] task disabled via DispatchTaskSettings; task_key=%s skip", task.task_key)
        return []

    clusters = _select_daily_clusters(
        schedule_date=schedule_date,
        cluster_types=cfg.resolve_cluster_types(),
        ignore_cluster_domains=cfg.ignore_cluster_domains,
        daily_shuffle_limit=cfg.daily_shuffle_limit,
    )
    report_from, report_to = _build_report_window(schedule_date, cfg.report_window_days_back)
    return [
        {
            "cluster_id": cluster.id,
            "cluster_domain": cluster.immute_domain,
            "schedule_date": schedule_date.isoformat(),
            "report_from_iso": report_from.isoformat(),  # 携带 tzinfo，形如 "2026-09-14T00:00:00+08:00"
            "report_to_iso": report_to.isoformat(),
        }
        for cluster in clusters
    ]


def _round_robin(
    batches: List[Tuple[PortraitReportTaskBase, List[Dict[str, Any]]]]
) -> List[Tuple[PortraitReportTaskBase, Dict[str, Any]]]:
    """按轮转顺序展开各 Task 的 items：A0, B0, A1, B1, ...；较短的 Task 取完后，其余按原顺序排在后面。"""
    ordered: List[Tuple[PortraitReportTaskBase, Dict[str, Any]]] = []
    max_len: int = max((len(items) for _task, items in batches), default=0)
    for rank in range(max_len):
        for task, items in batches:
            if rank < len(items):
                ordered.append((task, items[rank]))
    return ordered


def _ready_times(count: int, window_seconds: int, now: float) -> List[float]:
    """为按全局序号排列的 ``count`` 个 item 计算严格递增的 ``ready_at``。

    - ``window_seconds > 0``：在 ``[now, now + window)`` 内均摊，与 ``spread(window)`` 同语义；
    - ``window_seconds == 0``：以 1ms 步长排在 ``now`` 之前，首个 pump tick 即全部可出队，且保持轮转顺序。
    """
    if window_seconds > 0:
        step: float = window_seconds / max(1, count)
        return [now + idx * step for idx in range(count)]
    base_ts: float = now - count * _ZERO_WINDOW_STEP_SECONDS
    return [base_ts + idx * _ZERO_WINDOW_STEP_SECONDS for idx in range(count)]


def _submit(
    task: PortraitReportTaskBase,
    items: List[Dict[str, Any]],
    ready_times: List[float],
    schedule_date: date,
    window_seconds: int,
) -> None:
    """提交单个 Task 的 items（``ready_at`` 已按全局轮转序号算好）并打印结构化汇总日志。"""
    outcomes = task.submit(items, ready_at=lambda idx, _item: ready_times[idx])

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
            "[portrait_producer] partial admission failure: task_key=%s capacity_rejected=%d unavailable=%d "
            "(next daily beat will retry)",
            task.task_key,
            capacity_rejected,
            unavailable,
        )

    logger.info(
        "[portrait_producer] dispatch done: task_key=%s schedule_date=%s total=%d "
        "enqueued=%d duplicates=%d capacity_rejected=%d unavailable=%d deadline_expired=%d "
        "window_seconds=%d",
        task.task_key,
        schedule_date,
        len(items),
        enqueued,
        duplicates,
        capacity_rejected,
        unavailable,
        deadline_expired,
        window_seconds,
    )


def _portrait_task_classes() -> List[Type[PortraitReportTaskBase]]:
    """所有已注册的画像 Task 类（按注册顺序，即轮转顺序）。"""
    return [cls for cls in DISPATCH_REGISTRY.values() if issubclass(cls, PortraitReportTaskBase)]


@register_periodic_task(run_every=crontab(minute=0, hour=0))
def generate_cluster_portrait_report() -> None:
    """集群画像 —— DispatchQueue 版本 producer 入口（每日 0 点触发，覆盖所有已注册的画像 Task）。

    执行流程：
        1) 校验 ``env.ENABLE_DBM_AI``；
        2) 每个启用的画像 Task 按自身配置选集群、组装 items；
        3) 按轮转顺序展开所有 items，按全局序号统一计算 ``ready_at``；
        4) 各 Task 分别 ``submit``。
        单个 Task 在加载配置 / 选集群 / submit 任一阶段失败只记录日志并跳过，不影响其他 Task。
    """
    if not env.ENABLE_DBM_AI:
        logger.warning("[portrait_producer] AI not enabled (env.ENABLE_DBM_AI=False); skip")
        return

    schedule_date: date = timezone.localdate()
    batches: List[Tuple[PortraitReportTaskBase, List[Dict[str, Any]]]] = []
    for task_cls in _portrait_task_classes():
        try:
            task = task_cls()
            items = _build_items(task, schedule_date)
        except Exception:  # noqa: BLE001 - 单个 Task 选集群失败不阻塞其他 Task
            logger.exception("[portrait_producer] build items failed: task=%s", task_cls.__name__)
            continue
        if items:
            batches.append((task, items))
    if not batches:
        return

    ordered = _round_robin(batches)
    window_seconds: int = max(max(0, int(task.config.dispatch_spread_window_seconds)) for task, _items in batches)
    ready_times = _ready_times(len(ordered), window_seconds, now=time.time())

    ready_by_task: Dict[str, List[float]] = {task.task_key: [] for task, _items in batches}
    for (task, _item), ready_at in zip(ordered, ready_times):
        ready_by_task[task.task_key].append(ready_at)

    for task, items in batches:
        try:
            _submit(task, items, ready_by_task[task.task_key], schedule_date, window_seconds)
        except Exception:  # noqa: BLE001 - 单个 Task 投递失败不阻塞其他 Task
            logger.exception("[portrait_producer] submit failed: task_key=%s", task.task_key)
