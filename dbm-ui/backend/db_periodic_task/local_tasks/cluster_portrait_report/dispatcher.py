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
from typing import Any, List, Optional

from django.core.cache import cache
from django.db.models import F, IntegerField, Value
from django.db.models.functions import Mod
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.context_manager import start_new_span
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown

logger = logging.getLogger("root")

# ------------------------------ 默认配置 ------------------------------

# 错峰窗口：画像每个集群一次 AI 调用，每集群一个 task；
# 1000 个 task 平摊到 50 分钟内，避免瞬时打满 AI 服务。
# 灰度实测：30min 窗口内每 5min 会集中 110-137 次 AI 请求，触发下游 SDK 请求上限，
# 因此拉长到 50min，配合 worker 侧 rate_limit="10/m" 把每 5min 请求量压到 30-50。
# 窗口须严格短于 Redis broker visibility_timeout（默认 3600s / 1h），
# 否则 countdown 任务会被 broker 视为超时并重复投递（当前 3000s < 3600s，满足约束）。
_DEFAULT_DISPATCH_WINDOW_SECONDS: int = 50 * TimeUnit.MINUTE

# dispatch 锁 TTL：正常投递秒级完成、finally 主动释放；
# 兜底场景是 dispatcher 进程崩溃 / 卡死时，靠 TTL 自愈避免"永久泄漏"。
# 取 12h：覆盖手动补发场景（同一天内二次触发）不会与上一轮 dispatch 并发；
# 12h < 24h（下一次 beat 触发间隔），确保次日 beat 一定能抢到锁。
_DEFAULT_DISPATCH_LOCK_TIMEOUT: int = 12 * TimeUnit.HOUR

# 子任务软/硬超时：灰度实测单集群一次 AI 画像耗时 40s-150s，超过 5min 概率极低；
# 软超时 5min 触发 SoftTimeLimitExceeded 交给生成器兜底落 status=error/timeout 记录；
# 硬超时 8min 强制 kill worker 子进程，防止极端卡死时长期占用 worker 名额。
# 若灰度后 5min 误杀率 > 1%，可将两个常量分别回调到 10min / 15min。
_DEFAULT_BATCH_SOFT_TIME_LIMIT: int = 5 * TimeUnit.MINUTE
_DEFAULT_BATCH_TIME_LIMIT: int = 8 * TimeUnit.MINUTE

# 防重锁 TTL：按「集群域名 + 日期」防重，略长于 1 天即可回收 cache 条目；
# 防重语义在 key（带日期），不在 TTL 时长。不主动 delete，任务结束也不释锁。
_DEDUP_LOCK_TIMEOUT: int = 25 * TimeUnit.HOUR


class ClusterPortraitDispatcher(object):
    """集群画像报告通用分发器。

    职责：
      - 按 ``Cluster.id`` 升序取前 ``limit`` 个集群（灰度限流）；
      - 每个集群投递一个 Celery worker task（batch_size=1，避免串行 AI 调用超时）；
      - 通过 ``calculate_countdown`` 将各 task 错峰投递，削峰填谷；
      - 双层 Redis 锁：dispatch 锁（防 beat 抖动重入）+ 防重锁（按集群+日期，防重复生成）；
      - 只感知"如何调度"，不感知"如何生成画像"（生成细节由 ``worker_task`` 参数注入）。

    复用 ``check_expired_job_users`` 的调度骨架（dispatch 锁 + 错峰 + start_new_span + apply_async），
    差异：按 id 升序取前 N、每集群一个 task、cache.add 按集群+日期防重。

    使用方式：
      dispatcher = ClusterPortraitDispatcher(
          name="mysql",
          cluster_types=[ClusterType.TenDBHA, ...],
          worker_task=generate_cluster_portrait_report_batch,
          limit=1000,
      )
      dispatcher.dispatch()

    边界：
      - 集群总数为 0           -> 不投递任何子任务；
      - dispatch 锁未释放     -> 本次调用直接跳过（防止 beat 抖动导致的重复分发）；
      - 防重锁未释放           -> 该集群本次跳过（防止重跑重复生成画像记录）；
      - apply_async 失败      -> 主动删除防重锁，允许后续重试。
    """

    def __init__(
        self,
        name: str,
        cluster_types: List[ClusterType],
        worker_task: Any,
        limit: int,
        dispatch_window_seconds: int = _DEFAULT_DISPATCH_WINDOW_SECONDS,
        dispatch_lock_timeout: int = _DEFAULT_DISPATCH_LOCK_TIMEOUT,
        batch_soft_time_limit: int = _DEFAULT_BATCH_SOFT_TIME_LIMIT,
        batch_time_limit: int = _DEFAULT_BATCH_TIME_LIMIT,
        lock_key_prefix: Optional[str] = None,
    ) -> None:
        """初始化分发器。

        :param name: 逻辑名，如 "mysql"，用于生成锁 key 与日志前缀
        :param cluster_types: 画像覆盖的集群类型
        :param worker_task: Celery @app.task 装饰后的对象；签名固定为 (cluster_id, lock_key, schedule_date_str)
        :param limit: 灰度限流：按 Cluster.id 升序最多取前 N 个集群；0 表示不限
        :param dispatch_window_seconds: 错峰投递窗口秒数，默认 50 分钟
        :param dispatch_lock_timeout: dispatch 锁 timeout（秒），默认 12 小时
        :param batch_soft_time_limit: 子任务软超时（秒），默认 5 分钟
        :param batch_time_limit: 子任务硬超时（秒），默认 8 分钟
        :param lock_key_prefix: 锁 key 前缀；缺省为 f"cluster_portrait_report:{name}"
        """
        self.name: str = name
        self.cluster_types: List[ClusterType] = cluster_types
        self.worker_task: Any = worker_task
        self.limit: int = limit
        self.dispatch_window_seconds: int = dispatch_window_seconds
        self.dispatch_lock_timeout: int = dispatch_lock_timeout
        self.batch_soft_time_limit: int = batch_soft_time_limit
        self.batch_time_limit: int = batch_time_limit

        self._lock_key_prefix: str = lock_key_prefix or f"cluster_portrait_report:{name}"
        self._dispatch_lock_key: str = f"{self._lock_key_prefix}:dispatch"

    # -------- public --------

    def dispatch(self) -> None:
        """定时任务入口：加 dispatch 锁并触发一次分发。

        :return: None
        边界：dispatch_lock 未抢到 -> 直接跳过；异常 -> 记录 + 上抛。
        """
        if not cache.add(self._dispatch_lock_key, 1, timeout=self.dispatch_lock_timeout):
            logger.warning("dispatch skip, lock held: %s", self._dispatch_lock_key)
            return
        try:
            self._do_dispatch()
        except Exception:  # noqa
            logger.exception("dispatch failed: %s", self._dispatch_lock_key)
            raise
        finally:
            cache.delete(self._dispatch_lock_key)

    # -------- private --------

    def _do_dispatch(self) -> None:
        """遍历当日桶内集群，逐个加防重锁、错峰投递。

        灰度采样策略（跨日打散，避免同一批集群在轮转周期内固定在同一天）：
          - 设集群总数为 total、灰度上限为 self.limit；
          - 令 bucket_count = ceil(total / limit)，将集群按“(id + 日序数) % bucket_count”
            分为 bucket_count 个桶（日序数参与散列 -> 同一集群在不同日期会落到不同桶，
            新建集群仍会自然落入某个桶、不会遗漏）；
          - 按调度日期轮转：today_bucket = schedule_date.toordinal() % bucket_count；
          - 本日只画 today_bucket 号桶的集群，bucket_count 天内完整轮一次；
          - 跨日打散后，连续两天集群集合重合率期望 ≈ 1 / bucket_count（近似随机抽样）；
          - total <= limit 时退化为"全量画像"，与灰度前行为一致。

        :return: None
        """
        schedule_date = timezone.localdate()

        base_qs = Cluster.objects.filter(cluster_type__in=self.cluster_types)
        total_count: int = base_qs.count()

        # 按日轮转分桶：仅当总数超过灰度上限时才分桶，否则全量
        bucket_count: int = 0
        today_bucket: int = 0
        # 分桶策略标识，仅用于日志可观测：daily_shuffle 跨日打散 / stable_all 不分桶全量
        bucket_key_strategy: str = "stable_all"
        if self.limit and total_count > self.limit:
            # 向上取整，确保每桶集群数不超过 limit
            bucket_count = (total_count + self.limit - 1) // self.limit
            # toordinal() 是"公历日序数"，天然按天 +1，作为轮转索引稳定可复现
            day_ord: int = schedule_date.toordinal()
            today_bucket = day_ord % bucket_count
            # 分桶键 = (id + 日序数) % bucket_count：引入日期参与散列，同一集群在不同日期
            # 会落到不同桶，从而达到"每天集群集合不同"的效果；覆盖周期仍为 bucket_count 天。
            clusters_qs = (
                base_qs.annotate(
                    _bucket=Mod(
                        F("id") + Value(day_ord),
                        Value(bucket_count, output_field=IntegerField()),
                    )
                )
                .filter(_bucket=today_bucket)
                .order_by("id")
            )
            bucket_key_strategy = "daily_shuffle"
        else:
            clusters_qs = base_qs.order_by("id")
            if self.limit:
                clusters_qs = clusters_qs[: self.limit]

        clusters = list(clusters_qs)
        cluster_count = len(clusters)
        if cluster_count == 0:
            logger.info("dispatch skip, no cluster: name=%s", self.name)
            return

        scheduled, skipped_lock = 0, 0
        logger.info(
            "dispatch start: name=%s schedule_date=%s cluster_count=%d total=%d "
            "limit=%s bucket_count=%d today_bucket=%d dispatch_window_seconds=%d "
            "bucket_key_strategy=%s",
            self.name,
            schedule_date,
            cluster_count,
            total_count,
            self.limit,
            bucket_count,
            today_bucket,
            self.dispatch_window_seconds,
            bucket_key_strategy,
        )

        for index, cluster in enumerate(clusters):
            lock_key = f"{self._lock_key_prefix}:{cluster.immute_domain}:{schedule_date}"

            # 防重：按集群+日期，25h TTL（略长于 1 天，次日自动换新 key）
            if not cache.add(lock_key, 1, timeout=_DEDUP_LOCK_TIMEOUT):
                skipped_lock += 1
                logger.warning("portrait skip, lock held: lock_key=%s", lock_key)
                continue

            countdown = calculate_countdown(count=cluster_count, index=index, duration=self.dispatch_window_seconds)

            try:
                with start_new_span(self.worker_task):
                    self.worker_task.apply_async(
                        args=[cluster.id, lock_key, schedule_date.isoformat()],
                        countdown=countdown,
                        soft_time_limit=self.batch_soft_time_limit,
                        time_limit=self.batch_time_limit,
                    )
                scheduled += 1
                logger.info(
                    "portrait scheduled: lock_key=%s cluster=%s countdown=%ds",
                    lock_key,
                    cluster.immute_domain,
                    countdown,
                )
            except Exception:  # noqa
                logger.exception("portrait schedule failed: lock_key=%s", lock_key)
                # 投递失败要主动释放防重锁，允许后续重试
                cache.delete(lock_key)

        # 预估投递速率（仅用于日志观测，不参与调度决策）；
        # 300 = 5 * 60，将"投递总数 / 窗口内 5min 个数"换算为平均每 5 分钟投递量。
        # scheduled=0 或 window<=0 时兜底为 0.0，避免除零。
        if scheduled > 0 and self.dispatch_window_seconds > 0:
            avg_rate_per_5min: float = round(scheduled / (self.dispatch_window_seconds / 300), 2)
        else:
            avg_rate_per_5min = 0.0
        logger.info(
            "dispatch done: name=%s scheduled=%d skipped_lock=%d total=%d avg_rate_per_5min=%.2f",
            self.name,
            scheduled,
            skipped_lock,
            cluster_count,
            avg_rate_per_5min,
        )
