# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

临时账号巡检 —— 通用调度层。

设计要点 / 怎么做：
  - 抽象 MySQL / SQLServer 两条巡检链路的公共调度骨架：
      分片（Cluster.id % hash_cnt） + 错峰（calculate_countdown）
      + 双层 Redis 锁（dispatch 级 + batch 级） + apply_async 投递。
  - 具体"如何巡检一批集群"由调用方通过 `worker_task` 参数注入，本模块不感知 DB 引擎细节。
  - 与上下游边界：
      · 上游：task.py 中 @register_periodic_task 入口调用 `ExpiredJobUserDispatcher.dispatch()`；
      · 下游：调用方各自的 Celery worker 薄壳（`@app.task`），内部走 `run_batch_with_lock`
        统一处理"业务异常上抛 + finally 释放 batch 锁"。
"""
import logging
import math
from contextlib import contextmanager
from typing import Any, Iterator, List, Optional

from django.core.cache import cache
from django.db.models import QuerySet
from django.db.models.functions import Mod

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.context_manager import start_new_span
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown

logger = logging.getLogger("root")

# ------------------------------ 默认配置 ------------------------------

# 每批处理的集群数量上限；参考 skew 检测经验值，MySQL/SQLServer 均适用
_DEFAULT_BATCH_SIZE: int = 5

# 错峰窗口：巡检类任务默认 5 分钟内平摊，避免瞬时打爆 DRS。
# 取值依据：
#   - 单集群 RPC 正常 <10s；每批间隔 ≥ 2~3s 即可让 DRS "消化-空闲-消化"错开处理；
#   - 5min 对应典型规模（<600 集群、batch_size=5）每批间隔 ≥2.5s，足以稀释瞬时压力；
#   - 若集群数破千，可上调至 10~15min，或调大 batch_size 减少 hash_cnt。
_DEFAULT_DISPATCH_WINDOW_SECONDS: int = 5 * TimeUnit.MINUTE

# dispatch 锁 TTL：正常投递秒级完成、finally 主动释放；
# 兜底场景是 dispatcher 进程崩溃 / 卡死时，靠 TTL 自愈避免"永久泄漏"。
# 取 12h 的经验值：
#   - 覆盖手动补发场景（同一天内二次触发）不会与上一轮 dispatch 并发；
#   - 12h < 24h（下一次 beat 触发间隔），确保次日 beat 一定能抢到锁；
#   - 正常路径不受影响（finally 会立即 delete，不会等到 TTL）。
_DEFAULT_DISPATCH_LOCK_TIMEOUT: int = 12 * TimeUnit.HOUR

# batch 锁 TTL：正常路径由 worker 在 finally 中主动释放；
# 兜底场景是 worker 崩溃 / OOM / Pod 驱逐时靠 TTL 自愈。
# 取 12h 的经验值：
#   - 必须 ≥ (countdown 窗口 30min + broker 排队 + 硬超时 30min + 余量)；
#   - 与 dispatch 锁对齐，避免 batch 锁先释放、dispatch 锁还在时，被手动补发误抢占；
#   - 正常路径不受影响（finally 会立即 delete）。
_DEFAULT_BATCH_LOCK_TIMEOUT: int = 12 * TimeUnit.HOUR

# 子任务软/硬超时：DRS 单批 20 集群，正常 5~10 分钟内结束；超时说明卡死，直接 kill
_DEFAULT_BATCH_SOFT_TIME_LIMIT: int = 20 * TimeUnit.MINUTE
_DEFAULT_BATCH_TIME_LIMIT: int = 30 * TimeUnit.MINUTE


# ------------------------------ Celery worker 侧公共工具 ------------------------------


@contextmanager
def run_batch_with_lock(task_name: str, lock_key: str, cluster_count: int) -> Iterator[None]:
    """batch worker 通用生命周期管理：日志 + 异常上抛 + finally 释放 batch 锁。

    使用方式：
      with run_batch_with_lock("check_expired_job_users_for_mysql", lock_key, len(cluster_ids)):
          CheckExpiredJobUserForMysql(cluster_ids=cluster_ids).do_check()

    :param task_name: 任务名，仅用于日志前缀，便于运维排查
    :param lock_key: 与 dispatcher 约定的 batch 锁 key；无论成功/失败均在 finally 释放
    :param cluster_count: 本批集群数量，仅用于日志展示
    :return: 迭代器；yield 时执行调用方业务
    边界：
      - 调用方业务异常 -> 记录 exception 日志并向上抛出（Celery 会记录失败）；
      - 无论成功/失败，finally 均释放 batch 锁；锁自然过期后可能已被别人重新抢占，
        本上下文不做二次校验（拿锁的人负责释放，其它人只有等 TTL 或抢占）。
    """
    logger.info("[%s] batch start: task=%s lock_key=%s cluster_count=%d", lock_key, task_name, lock_key, cluster_count)
    try:
        yield
        logger.info(
            "[%s] batch done: task=%s lock_key=%s cluster_count=%d", lock_key, task_name, lock_key, cluster_count
        )
    except Exception:  # noqa
        logger.exception(
            "[%s] batch failed: task=%s lock_key=%s cluster_count=%d", lock_key, task_name, lock_key, cluster_count
        )
        raise
    finally:
        # 拿锁的人负责释放；即便锁已自然过期或被别人抢占，delete 也是幂等的
        cache.delete(lock_key)


# ------------------------------ 通用分发器 ------------------------------


class ExpiredJobUserDispatcher(object):
    """临时账号巡检通用分发器。

    职责：
      - 按 `Cluster.id % hash_cnt` 分片，将全量集群拆成多批；
      - 通过 `calculate_countdown` 将各批错峰投递到 Celery worker，削峰填谷；
      - 通过双层 Redis 锁（dispatch 级 + batch 级）避免重入 / 叠加；
      - 只感知"如何调度"，不感知"如何巡检"（巡检细节由 `worker_task` 参数注入）。

    使用方式：
      dispatcher = ExpiredJobUserDispatcher(
          name="mysql",
          cluster_types=[ClusterType.TenDBHA, ...],
          worker_task=check_expired_job_users_for_mysql_batch,
      )
      dispatcher.dispatch()

    边界：
      - 集群总数为 0        -> 不投递任何子任务；
      - 单批为空（分桶为空）-> 记录 warning 跳过，不占用锁；
      - dispatch 锁未释放   -> 本次调用直接跳过（防止 beat 抖动导致的重复分发）；
      - batch 锁未释放     -> 本批跳过（防止上一周期未跑完时重复投递）；
      - apply_async 失败    -> 主动删除 batch 锁，避免锁泄漏。

    分片语义（重要）：
      - `hash_cnt = ceil(cluster_count / batch_size)` 每次 dispatch 现算，会随集群总数
        增减（新建 / 迁移 / 下架）而变化；
      - 因此 batch 锁 key 中的 `hash_value`（形如 "check_expired_job_users:mysql:5"）
        仅代表"当前这次 dispatch 的分桶下标"，**不是稳定的集群分组标识**：
          · 同一个 Cluster.id 在不同周期可能落到不同的 hash 桶；
          · 同一个 lock_key 在不同周期覆盖的 cluster_ids 集合会漂移。
      - 所带来的实际影响：
          · 上一周期未释放的 batch 锁与本次分桶的集群集合并**不严格对应**，
            "跳过某桶"意味着"这轮先不重复投递该下标位"，而不是"跳过某组固定集群"；
          · 因巡检幂等（drop 前会重新查 Flow 状态），漂移不会引发数据一致性问题，
            集群最终都会在下一个周期被覆盖到；
      - 若未来需要"稳定分组"（例如按集群做限流 / 结果归档），应改用
        Cluster.id 直接作为 shard key，而不是当前的下标语义。
    """

    def __init__(
        self,
        name: str,
        cluster_types: List[ClusterType],
        worker_task: Any,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        dispatch_window_seconds: int = _DEFAULT_DISPATCH_WINDOW_SECONDS,
        dispatch_lock_timeout: int = _DEFAULT_DISPATCH_LOCK_TIMEOUT,
        batch_lock_timeout: int = _DEFAULT_BATCH_LOCK_TIMEOUT,
        batch_soft_time_limit: int = _DEFAULT_BATCH_SOFT_TIME_LIMIT,
        batch_time_limit: int = _DEFAULT_BATCH_TIME_LIMIT,
        lock_key_prefix: Optional[str] = None,
    ) -> None:
        """初始化分发器。

        :param name: 逻辑名，如 "mysql" / "sqlserver_ha"，用于生成锁 key 与日志前缀
        :param cluster_types: 巡检覆盖的集群类型（与 worker_task 内的业务类保持一致）
        :param worker_task: Celery @app.task 装饰后的对象；apply_async 的目标；
                            签名固定为 (cluster_ids, lock_key)。类型标为 Any 以避免
                            静态检查器无法识别 @app.task 装饰后类型（运行期实际为 celery Task）。
        :param batch_size: 每批最多多少个集群，默认 5
        :param dispatch_window_seconds: 错峰投递窗口秒数，默认 5 分钟
        :param dispatch_lock_timeout: dispatch 锁 timeout（秒），默认 10 分钟
        :param batch_lock_timeout: batch 锁 timeout（秒），默认 60 分钟
        :param batch_soft_time_limit: 子任务软超时（秒），默认 20 分钟
        :param batch_time_limit: 子任务硬超时（秒），默认 30 分钟
        :param lock_key_prefix: 锁 key 前缀；缺省为 f"check_expired_job_users:{name}"

        边界：cluster_types 中的类型合法性由业务巡检类自行校验。
        """
        self.name: str = name
        self.cluster_types: List[ClusterType] = cluster_types
        self.worker_task: Any = worker_task
        self.batch_size: int = batch_size
        self.dispatch_window_seconds: int = dispatch_window_seconds
        self.dispatch_lock_timeout: int = dispatch_lock_timeout
        self.batch_lock_timeout: int = batch_lock_timeout
        self.batch_soft_time_limit: int = batch_soft_time_limit
        self.batch_time_limit: int = batch_time_limit

        # 锁 key 前缀；便于运维在 Redis 中按前缀排查
        self._lock_key_prefix: str = lock_key_prefix or f"check_expired_job_users:{name}"

        # dispatch 级锁 key（全局唯一，防止 beat 抖动导致的分发重入）
        self._dispatch_lock_key: str = f"{self._lock_key_prefix}:dispatch"

    # -------- public --------

    def dispatch(self) -> None:
        """定时任务入口：加 dispatch 锁并触发一次分发。

        :return: None
        边界：dispatch_lock 未抢到 -> 直接跳过；异常 -> 记录 + 上抛。
        """
        # cache.add：仅当 key 不存在时才写入并返回 True，等价于 Redis SET NX；
        # 用作 dispatch 级"入口互斥锁"，防止 beat 抖动 / 手动补发导致同名 dispatch 并发。
        # timeout 是"锁的 TTL"（不是加锁动作的超时）——正常路径由 finally 主动 delete；
        # 兜底场景是 dispatcher 崩溃时靠 TTL 自愈，避免锁永久泄漏。
        if not cache.add(self._dispatch_lock_key, 1, timeout=self.dispatch_lock_timeout):
            logger.warning("[%s] dispatch skip, lock held: %s", self._lock_key_prefix, self._dispatch_lock_key)
            return
        try:
            self._do_dispatch()
        except Exception:  # noqa
            logger.exception("[%s] dispatch failed: %s", self._lock_key_prefix, self._dispatch_lock_key)
            raise
        finally:
            # 正常路径主动释放；即使异常/崩溃未走到这里，也有 TTL 兜底
            cache.delete(self._dispatch_lock_key)

    # -------- private --------

    def _batch_lock_key(self, hash_value: int) -> str:
        """生成本批 batch 锁 key。

        :param hash_value: 分桶下标
        :return: 形如 "check_expired_job_users:mysql:0" 的 lock key
        """
        return f"{self._lock_key_prefix}:{hash_value}"

    def _do_dispatch(self) -> None:
        """按分片粒度遍历、加 batch 锁、错峰投递。

        :return: None
        边界：见类 docstring；单批为空/锁被占均记录日志跳过。
        """
        clusters_q = Cluster.objects.filter(cluster_type__in=self.cluster_types)
        cluster_count = clusters_q.count()
        if cluster_count == 0:
            logger.info("[%s] dispatch skip, no cluster: name=%s", self._lock_key_prefix, self.name)
            return

        hash_cnt = math.ceil(cluster_count / self.batch_size)
        scheduled, skipped_lock, empty_batch = 0, 0, 0

        logger.info(
            "[%s] dispatch start: name=%s cluster_count=%d hash_cnt=%d batch_size=%d",
            self._lock_key_prefix,
            self.name,
            cluster_count,
            hash_cnt,
            self.batch_size,
        )

        for hash_value in range(hash_cnt):
            outcome = self._dispatch_one_batch(clusters_q=clusters_q, hash_cnt=hash_cnt, hash_value=hash_value)
            if outcome == "scheduled":
                scheduled += 1
            elif outcome == "skipped_lock":
                skipped_lock += 1
            elif outcome == "empty_batch":
                empty_batch += 1

        logger.info(
            "[%s] dispatch done: name=%s scheduled=%d skipped_lock=%d empty_batch=%d total_hash=%d",
            self._lock_key_prefix,
            self.name,
            scheduled,
            skipped_lock,
            empty_batch,
            hash_cnt,
        )

    def _dispatch_one_batch(self, clusters_q: QuerySet, hash_cnt: int, hash_value: int) -> str:
        """处理单个分桶：查 ids -> 抢锁 -> 投递。

        :param clusters_q: 全量集群 QuerySet（已限定 cluster_type）
        :param hash_cnt: 分桶总数
        :param hash_value: 当前分桶下标
        :return: "scheduled" | "skipped_lock" | "empty_batch" | "schedule_failed"
        边界：
          - 分桶无集群 -> "empty_batch"（不占锁）；
          - 抢锁失败   -> "skipped_lock"；
          - apply_async 抛异常 -> 主动删锁，返回 "schedule_failed"。
        """
        lock_key = self._batch_lock_key(hash_value)

        cluster_ids = list(
            clusters_q.annotate(id_hash_value=Mod("id", hash_cnt))
            .filter(id_hash_value=hash_value)
            .values_list("id", flat=True)
        )
        if not cluster_ids:
            logger.warning("[%s] empty batch: name=%s hash_value=%d", self._lock_key_prefix, self.name, hash_value)
            return "empty_batch"

        if not cache.add(lock_key, 1, timeout=self.batch_lock_timeout):
            logger.warning(
                "[%s] batch skip, lock held: name=%s lock_key=%s cluster_count=%d",
                self._lock_key_prefix,
                self.name,
                lock_key,
                len(cluster_ids),
            )
            return "skipped_lock"

        # 错峰投递：把 hash_cnt 个分桶平摊到 dispatch_window_seconds（默认 30min）时间窗口内，
        # 避免所有 batch 同一秒进入 worker 池后同时冲击 DRS / 下游 MySQL。
        # 返回值 countdown 单位为秒；hash_cnt=1 时函数内部会返回 0（无需错峰）。
        # 具体实现：backend/db_periodic_task/utils.py::calculate_countdown
        countdown = calculate_countdown(
            count=hash_cnt,
            index=hash_value,
            duration=self.dispatch_window_seconds,
        )

        try:
            # start_new_span：开启一段分布式追踪 span（APM / OpenTelemetry），
            # 把"dispatcher 投递 -> broker -> worker 消费执行"串成同一条 trace，
            # 便于在观测平台看到完整调用链路。传入 self.worker_task 用作 span 名。
            with start_new_span(self.worker_task):
                # apply_async：把消息投递到 Celery broker（RabbitMQ），本函数毫秒级返回，
                # 真正执行发生在另一个 worker 进程。参数说明：
                #   - args             : 传给 worker_task 的位置参数 (cluster_ids, lock_key)
                #   - countdown        : 由 broker 保留 X 秒后再派发给 worker（错峰用）
                #   - soft_time_limit  : 软超时，超过后在 worker 内部抛 SoftTimeLimitExceeded
                #                        （业务可捕获做清理，如释放连接 / 打日志）
                #   - time_limit       : 硬超时，超过直接 SIGKILL worker 进程，防止卡死
                # 注意：time_limit 从"worker 开始执行"计时，不含 countdown 与 broker 排队。
                self.worker_task.apply_async(
                    args=[cluster_ids, lock_key],
                    countdown=countdown,
                    soft_time_limit=self.batch_soft_time_limit,
                    time_limit=self.batch_time_limit,
                )
            logger.info(
                "[%s] batch scheduled: name=%s lock_key=%s hash_value=%d cluster_count=%d countdown=%ds",
                self._lock_key_prefix,
                self.name,
                lock_key,
                hash_value,
                len(cluster_ids),
                countdown,
            )
            return "scheduled"
        except Exception:  # noqa
            logger.exception(
                "[%s] batch schedule failed: name=%s lock_key=%s hash_value=%d cluster_count=%d",
                self._lock_key_prefix,
                self.name,
                lock_key,
                hash_value,
                len(cluster_ids),
            )
            # 投递失败要主动释放刚拿到的 batch 锁，避免"锁泄漏 -> 后续周期一直跳过本桶"
            cache.delete(lock_key)
            return "schedule_failed"
