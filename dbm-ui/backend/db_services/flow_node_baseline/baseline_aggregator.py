# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

BaselineAggregator：flow 节点耗时基线聚合器。

模块职责：
  - 接收 NodeDurationSample 流，按 (ticket_type, bk_biz_id, code, normalized_name) 四维聚合
  - 用 Welford 在线算法维护 mean / stddev（O(1) 增量合并）
  - 保留原始耗时数组用于每次 flush 时重算 P50/P90/P95/P99（方案 A）
  - 判定 distribution_type（依据 stddev/mean 变异系数）与 is_reliable（依据 sample_count）
  - upsert 到 FlowNodeDurationBaseline 表

上下游边界：
  - 上游：FlowSampleCollector 吐样本流；NameNormalizer 提供 normalized_name
  - 下游：FlowNodeDurationBaseline（写库）

设计取舍：
  - 分位数用方案 A（每次 flush 时全量排序）：
      * 存量场景：一次性 rebuild 时一次性算完，samples list 用完即弃
      * 增量场景：需从 DB 读回历史耗时（不可行）→ 因此增量更新分位数时会做"近似合并"，
                   即把新 batch 的 P95 与历史 P95 加权平均，作为妥协；
                   如需绝对精确，需上层触发定期 rebuild
  - 全局基线（bk_biz_id=0）由调用方 (FlowBaselineService) 显式聚合，Aggregator 本身只按
    传入的 bk_biz_id 分组
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from backend.db_report.models import DistributionType, FlowNodeDurationBaseline
from backend.db_services.flow_node_baseline.constants import (
    BASELINE_MIN_RELIABLE_SAMPLES,
    DIST_NARROW_UNIMODAL_CV,
    DIST_WIDE_UNIMODAL_CV,
)
from backend.db_services.flow_node_baseline.sample_collector import NodeDurationSample

logger = logging.getLogger("root")


# =============================================================================
# Welford 在线算法：O(1) 增量合并 mean / M2 / stddev
# -----------------------------------------------------------------------------
# 参考：Welford's online algorithm（Knuth TAOCP Vol.2）
#   mean_new = mean_old + (x - mean_old) / n_new
#   M2_new   = M2_old + (x - mean_old) * (x - mean_new)
#   var      = M2 / n     （样本方差）
#   stddev   = sqrt(var)
# 优势：数值稳定，支持增量合并；只需 (count, mean, m2) 三元组即可 O(1) 添加新样本
# =============================================================================


@dataclass
class WelfordAccumulator:
    """Welford 在线均值/方差累计器（可与已有基线合并）。

    职责：
      - 单条样本：add(x) 累计 count / mean / m2
      - 与已有基线合并：merge_from_persisted(count, mean, m2) 加载历史累计
      - 输出：mean / stddev

    使用方式：
        acc = WelfordAccumulator()
        acc.merge_from_persisted(prev_count=100, prev_mean=5.2, prev_m2=42.0)
        acc.add(6)
        acc.add(7)
        # acc.mean, acc.stddev 可读

    线程安全：否（每个四维 key 独立一个实例，聚合过程在单线程内）
    边界：
      - count == 0 时 stddev 返回 0.0（无样本无方差）
      - count == 1 时 stddev 返回 0.0（单样本无方差）
    """

    #: 累计样本数
    count: int = 0
    #: 累计均值（秒）
    mean: float = 0.0
    #: Welford M2 中间量（sum((x - mean)^2)）
    m2: float = 0.0

    def add(self, value: float) -> None:
        """添加单条样本并更新累计量。

        :param value: 单条耗时（秒），必须 > 0
        """
        self.count += 1
        delta: float = value - self.mean
        self.mean += delta / self.count
        delta2: float = value - self.mean
        self.m2 += delta * delta2

    def merge_from_persisted(self, prev_count: int, prev_mean: float, prev_m2: float) -> None:
        """从 DB 已持久化的 (count, mean, m2) 加载历史累计，用于增量合并。

        :param prev_count: 已有样本数
        :param prev_mean: 已有均值
        :param prev_m2: 已有 M2 中间量
        边界：仅在实例首次使用（count == 0）时可加载；否则会破坏累计不变式
        """
        if self.count != 0:
            logger.warning("[WelfordAccumulator] merge_from_persisted called on non-empty accumulator; skipped")
            return
        self.count = int(prev_count or 0)
        self.mean = float(prev_mean or 0.0)
        self.m2 = float(prev_m2 or 0.0)

    @property
    def stddev(self) -> float:
        """当前样本标准差（总体标准差近似；样本数 <=1 返回 0）。"""
        if self.count <= 1:
            return 0.0
        return (self.m2 / self.count) ** 0.5


@dataclass
class _BaselineBucket:
    """单个四维 key 的聚合中间态；仅存活于一次 flush 前的内存中。

    :ivar welford: Welford 累计器（增量算 mean/stddev）
    :ivar durations: 本轮 flush 前收集的所有耗时样本；flush 时用来算分位数
    :ivar min_seconds: 最小值；随样本更新
    :ivar max_seconds: 最大值；随样本更新
    :ivar last_sample_finished_at: 本轮见到的最新样本时间
    """

    welford: WelfordAccumulator = field(default_factory=WelfordAccumulator)
    durations: List[int] = field(default_factory=list)
    min_seconds: float = 0.0
    max_seconds: float = 0.0
    last_sample_finished_at: Optional[datetime] = None

    def observe(self, duration: int, finished_at: datetime) -> None:
        """记录一条耗时样本到本 bucket。"""
        self.welford.add(duration)
        self.durations.append(duration)

        if self.welford.count == 1:
            # 首次记录：初始化 min/max
            self.min_seconds = duration
            self.max_seconds = duration
        else:
            if duration < self.min_seconds:
                self.min_seconds = duration
            if duration > self.max_seconds:
                self.max_seconds = duration

        if self.last_sample_finished_at is None or finished_at > self.last_sample_finished_at:
            self.last_sample_finished_at = finished_at


class BaselineAggregator:
    """flow 节点耗时基线聚合器（顶层入口）。

    使用姿势：
        aggregator = BaselineAggregator(mode="rebuild")
        for sample in collector.iter_samples(...):
            normalized_name = normalizer.normalize(...).normalized_name
            aggregator.accumulate(sample, normalized_name)
        aggregator.flush_to_db()

    支持两种运行模式（构造时指定）：
      - "rebuild"：全量重建；flush 前 会先删除对应四维范围的历史记录，再全新写入
                    分位数由本轮全部样本 100% 精确计算
      - "incremental"：增量合并；flush 时先读取 DB 已有 baseline，
                        用 Welford merge_from_persisted 合并累计量；
                        分位数走近似路径（本轮样本自身分位数，与历史分位数按样本数加权融合）

    线程安全：否（内部字典无锁；跨线程请每线程独立实例）
    副作用：写 FlowNodeDurationBaseline 表
    边界：
      - 未调用 flush_to_db 前，数据只在内存
      - 大批量场景应分片调用 flush_to_db，避免内存膨胀
    """

    #: 模式常量
    MODE_REBUILD: str = "rebuild"
    MODE_INCREMENTAL: str = "incremental"

    def __init__(self, mode: str = "rebuild") -> None:
        """:param mode: "rebuild" 或 "incremental"；默认 rebuild"""
        if mode not in (self.MODE_REBUILD, self.MODE_INCREMENTAL):
            raise ValueError(f"invalid mode: {mode}")
        self._mode: str = mode

        #: 四维 key → bucket 的内存字典
        self._buckets: Dict[Tuple[str, int, str, str], _BaselineBucket] = {}

        #: 本轮已 accumulate 的样本数（观测用）
        self._observed_count: int = 0

        #: rebuild/repair 场景下，purge 前由 service 快照的 (4 元组 -> 老 baseline_version)。
        #  create 分支会用 old + 1；找不到则回退为 1。默认空 dict 即可（新库场景）。
        self._version_snapshot: Dict[Tuple[str, int, str, str], int] = {}

        #: rebuild/repair 场景下，purge 前由 service 快照的 (4 元组 -> 老 baseline_version)。
        #  create 分支会用 old + 1；找不到则回退为 1。默认空 dict 即可（新库场景）。
        self._version_snapshot: Dict[Tuple[str, int, str, str], int] = {}

    # =========================================================================
    # 对外主入口
    # =========================================================================

    def set_version_snapshot(self, snapshot: Dict[Tuple[str, int, str, str], int]) -> None:
        """由 service 注入 purge 前的 baseline_version 快照，用于 rebuild/repair 覆写后
        延续版本号自增（create 分支使用 old + 1）。

        :param snapshot: {(ticket_type, bk_biz_id, component_code, normalized_name): old_version}
        边界：
          - 传入 None / 空 dict：等价于清空快照（后续 create 一律为 1）
          - 应在 accumulate 之前调用；也允许在 flush 前的任意时刻调用（不影响累积）
        """
        self._version_snapshot = dict(snapshot or {})

    def accumulate(self, sample: NodeDurationSample, normalized_name: str) -> None:
        """累计单条样本；调用方需先通过 NameNormalizer 得到 normalized_name。

        :param sample: FlowSampleCollector 吐出的样本
        :param normalized_name: NameNormalizer 归一化后的 name（作为四维 key 之一）
        边界：
          - normalized_name 为空 → 跳过（无法作为 key）
          - duration_seconds 已由 collector 保证在合法区间
        """
        if not normalized_name:
            return

        key: Tuple[str, int, str, str] = (
            sample.ticket_type,
            sample.bk_biz_id,
            sample.component_code,
            normalized_name,
        )
        bucket: _BaselineBucket = self._buckets.setdefault(key, _BaselineBucket())
        bucket.observe(sample.duration_seconds, sample.finished_at)
        self._observed_count += 1

    def flush_to_db(self) -> int:
        """把内存中的聚合结果写入 FlowNodeDurationBaseline 表。

        :return: 本次 flush 写入/更新的行数
        边界：
          - rebuild 模式：写入前不做删除（清空由 FlowBaselineService 显式控制，避免误删）
          - incremental 模式：与已有基线做 Welford 合并
          - flush 后清空内部 buckets，可继续 accumulate 下一批
        """
        written: int = 0

        # 每个 key 独立事务，避免单条失败拖垮整个 flush
        for key, bucket in self._buckets.items():
            try:
                self._flush_single(key, bucket)
                written += 1
            except Exception as err:
                logger.exception("[BaselineAggregator] flush single key failed, key=%s err=%s", key, err)

        # 清空内存，便于 GC
        self._buckets.clear()
        return written

    # =========================================================================
    # 内部：单 key 落库
    # =========================================================================

    def _flush_single(self, key: Tuple[str, int, str, str], bucket: _BaselineBucket) -> None:
        """把单个四维 key 的 bucket 落库；根据 mode 决定合并策略。"""
        ticket_type, bk_biz_id, component_code, normalized_name = key

        with transaction.atomic(using="report_db"):
            existing: Optional[FlowNodeDurationBaseline] = (
                FlowNodeDurationBaseline.objects.select_for_update()
                .filter(
                    ticket_type=ticket_type,
                    bk_biz_id=bk_biz_id,
                    component_code=component_code,
                    normalized_name=normalized_name,
                )
                .first()
            )

            # 增量模式：与 DB 已有累计合并
            if self._mode == self.MODE_INCREMENTAL and existing is not None:
                # Welford 合并：把 DB 里的累计导入到本 bucket 的 welford
                merged_welford: WelfordAccumulator = self._merge_welford(bucket.welford, existing)
                merged_min: float = min(bucket.min_seconds, existing.min_seconds or bucket.min_seconds)
                merged_max: float = max(bucket.max_seconds, existing.max_seconds or bucket.max_seconds)

                # 分位数：本轮精确 + 历史 P95/P99 加权融合
                new_p50, new_p90, new_p95, new_p99 = self._compute_percentiles(bucket.durations)
                p50: float = self._weighted_avg(
                    new_p50, bucket.welford.count, existing.p50_seconds, existing.sample_count
                )
                p90: float = self._weighted_avg(
                    new_p90, bucket.welford.count, existing.p90_seconds, existing.sample_count
                )
                p95: float = self._weighted_avg(
                    new_p95, bucket.welford.count, existing.p95_seconds, existing.sample_count
                )
                p99: float = self._weighted_avg(
                    new_p99, bucket.welford.count, existing.p99_seconds, existing.sample_count
                )

                self._upsert(
                    existing=existing,
                    ticket_type=ticket_type,
                    bk_biz_id=bk_biz_id,
                    component_code=component_code,
                    normalized_name=normalized_name,
                    welford=merged_welford,
                    p50=p50,
                    p90=p90,
                    p95=p95,
                    p99=p99,
                    min_v=merged_min,
                    max_v=merged_max,
                    last_sample_finished_at=bucket.last_sample_finished_at,
                    bump_version=False,
                )
                return

            # rebuild 模式，或者 incremental 但 DB 无历史
            p50, p90, p95, p99 = self._compute_percentiles(bucket.durations)
            self._upsert(
                existing=existing,
                ticket_type=ticket_type,
                bk_biz_id=bk_biz_id,
                component_code=component_code,
                normalized_name=normalized_name,
                welford=bucket.welford,
                p50=p50,
                p90=p90,
                p95=p95,
                p99=p99,
                min_v=bucket.min_seconds,
                max_v=bucket.max_seconds,
                last_sample_finished_at=bucket.last_sample_finished_at,
                bump_version=(self._mode == self.MODE_REBUILD),
            )

    def _upsert(
        self,
        existing: Optional[FlowNodeDurationBaseline],
        ticket_type: str,
        bk_biz_id: int,
        component_code: str,
        normalized_name: str,
        welford: WelfordAccumulator,
        p50: float,
        p90: float,
        p95: float,
        p99: float,
        min_v: float,
        max_v: float,
        last_sample_finished_at: Optional[datetime],
        bump_version: bool,
    ) -> None:
        """写入或更新 FlowNodeDurationBaseline 单行。"""
        distribution_type: str = self._classify_distribution(welford.count, welford.mean, welford.stddev)
        is_reliable: bool = (
            welford.count >= BASELINE_MIN_RELIABLE_SAMPLES and distribution_type != DistributionType.UNRELIABLE.value
        )

        if existing is None:
            # rebuild/repair 覆写场景：purge 前 service 已把老版本号快照传入；这里 old + 1 落库
            snapshot_key: Tuple[str, int, str, str] = (ticket_type, bk_biz_id, component_code, normalized_name)
            prev_version: int = int(self._version_snapshot.get(snapshot_key, 0) or 0)
            new_version: int = prev_version + 1 if prev_version > 0 else 1
            FlowNodeDurationBaseline.objects.create(
                ticket_type=ticket_type,
                bk_biz_id=bk_biz_id,
                component_code=component_code,
                normalized_name=normalized_name,
                sample_count=welford.count,
                mean_seconds=welford.mean,
                stddev_seconds=welford.stddev,
                m2_accumulator=welford.m2,
                p50_seconds=p50,
                p90_seconds=p90,
                p95_seconds=p95,
                p99_seconds=p99,
                min_seconds=min_v,
                max_seconds=max_v,
                distribution_type=distribution_type,
                is_reliable=is_reliable,
                last_sample_finished_at=last_sample_finished_at or timezone.now(),
                baseline_version=new_version,
            )
            return

        existing.sample_count = welford.count
        existing.mean_seconds = welford.mean
        existing.stddev_seconds = welford.stddev
        existing.m2_accumulator = welford.m2
        existing.p50_seconds = p50
        existing.p90_seconds = p90
        existing.p95_seconds = p95
        existing.p99_seconds = p99
        existing.min_seconds = min_v
        existing.max_seconds = max_v
        existing.distribution_type = distribution_type
        existing.is_reliable = is_reliable
        if last_sample_finished_at:
            existing.last_sample_finished_at = last_sample_finished_at
        if bump_version:
            existing.baseline_version = (existing.baseline_version or 1) + 1
        # 注意：不要把 update_at 放入 update_fields
        #   1) 本项目 AuditedModel 的字段名是 update_at（非 Django 惯例的 updated_at），
        #      写错名字会抛 FieldDoesNotExist；
        #   2) update_at 已由 auto_now=True 在 save() 时自动刷新，无需显式列出。
        existing.save(
            update_fields=[
                "sample_count",
                "mean_seconds",
                "stddev_seconds",
                "m2_accumulator",
                "p50_seconds",
                "p90_seconds",
                "p95_seconds",
                "p99_seconds",
                "min_seconds",
                "max_seconds",
                "distribution_type",
                "is_reliable",
                "last_sample_finished_at",
                "baseline_version",
            ]
        )

    # =========================================================================
    # 内部：Welford 合并 & 分位数 & 分布形态
    # =========================================================================

    @staticmethod
    def _compute_percentiles(durations: List[int]) -> Tuple[float, float, float, float]:
        """计算 P50/P90/P95/P99 分位数。

        :return: (p50, p90, p95, p99)
        边界：durations 为空返回 (0, 0, 0, 0)
        """
        if not durations:
            return 0.0, 0.0, 0.0, 0.0

        # 使用 statistics.quantiles 计算分位数（method="inclusive" 对齐通用统计习惯）
        # 注意：对于极小样本量（n<4），quantiles 可能返回不稳定值，此时退化为 min/max
        n: int = len(durations)
        ordered: List[int] = sorted(durations)
        if n == 1:
            v: float = float(ordered[0])
            return v, v, v, v

        # 直接按索引取分位数，稳健且可解释
        p50: float = float(ordered[min(n - 1, int(n * 0.50))])
        p90: float = float(ordered[min(n - 1, int(n * 0.90))])
        p95: float = float(ordered[min(n - 1, int(n * 0.95))])
        p99: float = float(ordered[min(n - 1, int(n * 0.99))])
        return p50, p90, p95, p99

    @staticmethod
    def _weighted_avg(new_v: float, new_n: int, old_v: float, old_n: int) -> float:
        """样本数加权平均，用于增量场景下分位数的近似融合。

        :return: (new_v * new_n + old_v * old_n) / (new_n + old_n)
        边界：分母 <=0 时返回 new_v
        """
        total: int = int(new_n or 0) + int(old_n or 0)
        if total <= 0:
            return float(new_v)
        return (float(new_v) * (new_n or 0) + float(old_v or 0) * (old_n or 0)) / total

    @staticmethod
    def _classify_distribution(count: int, mean: float, stddev: float) -> str:
        """依据样本数和变异系数判定分布形态。

        判定规则（constants 中定义阈值）：
          - count < BASELINE_MIN_RELIABLE_SAMPLES → UNRELIABLE
          - CV = stddev / mean:
              * <= DIST_NARROW_UNIMODAL_CV (0.5)  → NARROW_UNIMODAL
              * <= DIST_WIDE_UNIMODAL_CV   (2.0)  → WIDE_UNIMODAL
              * >  DIST_WIDE_UNIMODAL_CV          → HEAVY_TAILED
          - mean == 0 时无法算 CV → UNRELIABLE
        """
        if count < BASELINE_MIN_RELIABLE_SAMPLES:
            return DistributionType.UNRELIABLE.value
        if mean <= 0.0:
            return DistributionType.UNRELIABLE.value

        cv: float = stddev / mean
        if cv <= DIST_NARROW_UNIMODAL_CV:
            return DistributionType.NARROW_UNIMODAL.value
        if cv <= DIST_WIDE_UNIMODAL_CV:
            return DistributionType.WIDE_UNIMODAL.value
        return DistributionType.HEAVY_TAILED.value

    # =========================================================================
    # 观测用
    # =========================================================================

    @property
    def observed_count(self) -> int:
        """本轮 accumulate 收到的样本数。"""
        return self._observed_count

    @property
    def bucket_count(self) -> int:
        """当前内存中不同四维 key 的数量。"""
        return len(self._buckets)
