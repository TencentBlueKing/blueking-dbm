# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

FlowBaselineService：flow 节点耗时基线服务的顶层编排类。

模块职责：
  - 编排 FlowSampleCollector + NameNormalizer + BaselineAggregator 三大通用组件
  - 对外暴露 3 个入口：rebuild（全量重建）/ incremental_run（每日增量）/ repair（定点修复）
  - 管理 FlowNodeBaselineWatermark 水位读写
  - 维护 bk_biz_id=0 全局基线（业务基线的镜像聚合）
  - 分片处理时释放 NameNormalizer 内存缓存，控制存量场景内存占用

上下游边界：
  - 上游：Command（存量/修复入口）与 celery task（增量入口）
  - 下游：FlowSampleCollector / NameNormalizer / BaselineAggregator / FlowNodeDurationBaseline / FlowNodeBaselineWatermark

设计取舍：
  - 全局基线（bk_biz_id=0）通过再跑一次 aggregator（不带 bk_biz_id 分组）实现，代价是内存里样本走两遍；
    收益是查询时无需 SQL SUM，直接查表可得；权衡后选择"多消耗内存换查询简单"
  - 增量任务的水位以 (ticket_type, bk_biz_id) 为粒度记录，粒度足够细，避免一个业务出问题拖累其它
  - **rebuild / incremental_run 的公开入参不再暴露 bk_biz_ids**：
      * 全局基线是"所有业务样本合体"的口径，只重建部分业务会导致全局基线口径失真
      * 内部实现层（_do_rebuild / _iter_shards / _purge_baselines 等）仍保留 bk_biz_ids 参数通道，
        便于未来若不再维护全局基线时，可低成本恢复"按业务过滤"的能力
  - **repair 走独立通道，不重建全局基线**：
      * 仅清理并重建业务级 (bk_biz_id ∈ ids, ticket_type ∈ types) 的基线记录
      * 完全跳过 bk_biz_id=0 的清理与写入，避免用局部样本污染全局基线
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Set, Tuple

from django.db import transaction
from django.utils import timezone

from backend.db_report.models import FlowNodeBaselineWatermark, FlowNodeDurationBaseline
from backend.db_services.flow_node_baseline.baseline_aggregator import BaselineAggregator
from backend.db_services.flow_node_baseline.constants import (
    GLOBAL_BASELINE_BK_BIZ_ID,
    INCREMENTAL_DEFAULT_LOOKBACK_DAYS,
    STOCK_DEFAULT_LOOKBACK_DAYS,
)
from backend.db_services.flow_node_baseline.name_normalizer import NameNormalizer
from backend.db_services.flow_node_baseline.sample_collector import FlowSampleCollector, NodeDurationSample

logger = logging.getLogger("root")


@dataclass
class BaselineRunSummary:
    """一次基线任务运行的统计摘要，返回给调用方（Command / celery）。

    :ivar mode: 运行模式（'rebuild' / 'incremental' / 'repair'）
    :ivar since: 时间窗起点
    :ivar until: 时间窗终点
    :ivar shards_processed: 已处理的 (ticket_type, bk_biz_id) 分片数
    :ivar samples_collected: Collector 吐出的原始样本数
    :ivar samples_accumulated: 有效聚合的样本数（含 normalized_name 非空）
    :ivar buckets_written: 落库的四维 key 数（含全局基线）
    :ivar failures: 失败分片列表
    """

    mode: str
    since: datetime
    until: datetime
    shards_processed: int = 0
    samples_collected: int = 0
    samples_accumulated: int = 0
    buckets_written: int = 0
    failures: List[Tuple[str, int, str]] = field(default_factory=list)  # (ticket_type, bk_biz_id, err_msg)

    def as_dict(self) -> Dict:
        """转换为可打印/可序列化的 dict。"""
        return {
            "mode": self.mode,
            "since": self.since.isoformat() if self.since else None,
            "until": self.until.isoformat() if self.until else None,
            "shards_processed": self.shards_processed,
            "samples_collected": self.samples_collected,
            "samples_accumulated": self.samples_accumulated,
            "buckets_written": self.buckets_written,
            "failure_count": len(self.failures),
            "failures": [f"{tt}/biz={biz}: {msg}" for tt, biz, msg in self.failures[:20]],
        }


class FlowBaselineService:
    """flow 节点耗时基线服务（顶层编排）。

    职责：
      - rebuild(): 全量重建；清空指定 ticket_types 范围后从 FlowSampleCollector 重头聚合
                   （所有业务参与，同步维护全局基线 bk_biz_id=0）
      - incremental_run(): 每日增量；读水位 → 采样 → Welford 合并 → 推进水位
                           （所有业务参与，同步维护全局基线 bk_biz_id=0）
      - repair(): 定点修复；仅重建指定业务级基线 (bk_biz_ids × ticket_types)，**不动全局基线**

    使用姿势：
        service = FlowBaselineService()
        summary = service.rebuild(ticket_types=["MYSQL_PARTITION_V2"])
        # summary.as_dict() 返回运行统计

    线程安全：否（内部持有 NameNormalizer 单实例，含内存缓存；每线程独立 service 实例）
    副作用：读写 FlowNodeDurationBaseline / FlowNodeBaselineWatermark / FlowNodeNameAlias；调用 LLM
    边界：
      - rebuild / incremental_run：不接受 bk_biz_ids，永远全业务参与
      - repair：bk_biz_ids / ticket_types 必填，仅业务级基线，不清也不写全局基线
      - 分片失败仅记录到 summary.failures，不中断整体流程
    """

    #: 单次 flush 前累计的最大样本数；超过则强制 flush，避免内存膨胀
    #: 依据：单条样本内存 ~200B，10 万样本约 20MB，是安全上限
    _FLUSH_THRESHOLD_SAMPLES: int = 100_000

    def __init__(self) -> None:
        """无参构造；内部持有 Collector / Normalizer 单实例。

        Aggregator 每次运行独立创建（因为 rebuild / incremental 模式不同）。
        """
        self._collector: FlowSampleCollector = FlowSampleCollector()
        self._normalizer: NameNormalizer = NameNormalizer()

    # =========================================================================
    # 入口 1：全量重建（Command 存量入口）
    # =========================================================================

    def rebuild(
        self,
        ticket_types: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        dry_run: bool = False,
    ) -> BaselineRunSummary:
        """全量重建基线（存量初始化 + 手动重跑均走此路径）。

        重要约束：
          - **不接受 bk_biz_ids 过滤**。全局基线（bk_biz_id=0）是所有业务合体口径，
            若只重建部分业务，全局基线会丢失其它业务的样本贡献，口径失真。
          - 若需修复单个业务的业务级基线，请使用 repair()。

        :param ticket_types: 只重建这些单据类型；None 表示全量单据类型
        :param since: 时间窗起点；None 使用 STOCK_DEFAULT_LOOKBACK_DAYS 回溯
        :param until: 时间窗终点；None 使用当前时间
        :param dry_run: 只统计不写库；供调试与容量评估使用
        :return: BaselineRunSummary
        边界：
          - 会清空匹配 ticket_types 范围内的 FlowNodeDurationBaseline 记录（含 bk_biz_id=0，dry_run=False 时）
          - 会同步维护 bk_biz_id=0 全局基线
          - 内部按 (ticket_type, bk_biz_id) 分片，每分片 flush 后清 normalizer 内存缓存

        运维预期（LLM 调用量级与耗时）：
          - LLM 调用**仅由 NameNormalizer 触发**，触发条件为"新 cleaned_name **且**同
            (ticket_type, component_code) 下已存在归一化类别"。以下路径**均不调 LLM**：
              * cleaned_name 命中 FlowNodeNameAlias 表（含内存缓存）
              * 该 (ticket_type, component_code) 下首次出现任意类别（FIRST_SEEN 分支）
              * raw_name 清洗后为空
          - 单次 LLM 调用最坏耗时 ≈ LLM_CALL_TIMEOUT_SECONDS × (LLM_CALL_RETRY_TIMES + 1)
            （当前配置 = 20s × 2 = 40s）；正常成功耗时通常在 1~5s。
          - LLM 调用次数上界：Σ over (ticket_type, component_code) 分片 [ unique_cleaned_name_count - 1 ]，
            实际远小于"unique(tt, code, cleaned_name) 组合总数"，因为大量样本会命中
            已有 alias 或走 FIRST_SEEN 分支。单个 (tt, code) 下的类别数受
            CATEGORIES_HARD_LIMIT 熔断（当前 100），也就是单分片 LLM 调用数硬上限 ≤ 100。
          - 由于 _do_rebuild 是**单线程按分片串行**执行，LLM 调用天然被串行化，
            QPS 天然低于 1，不会打爆上游服务；但代价是**总耗时线性增长于全库 LLM 调用次数**。
          - **首次全量存量初始化**（cleaned_name 全部未见过）耗时可能显著：
            以 N 个待归一化类别、单次 LLM 5s 计，总耗时 ≈ N × 5s，建议按 --ticket-type
            分批跑；命令层面提供 --dry-run 做容量评估。
          - **第二次及以后运行**（全部命中 alias 表）几乎不再调 LLM，耗时主要由样本
            聚合与 DB 读写决定。
          - 若上游 LLM 服务波动，失败请求会走 LLM_FALLBACK 路径：
            normalized_name = cleaned_name 且 needs_review=True，不阻塞 rebuild，
            事后可通过筛选 FlowNodeNameAlias.needs_review=True 交给 DBA 人工核对。
        """
        # 内部通道保留 bk_biz_ids 参数（此处永远传 None），便于未来若不再维护全局基线时，
        # 快速恢复"按业务过滤"的重建能力
        return self._do_rebuild(
            bk_biz_ids=None,
            ticket_types=ticket_types,
            since=since,
            until=until,
            dry_run=dry_run,
            maintain_global=True,
            advance_watermarks=True,
        )

    # =========================================================================
    # 入口 2：每日增量（celery 定时任务入口）
    # =========================================================================

    def incremental_run(
        self,
        ticket_types: Optional[List[str]] = None,
    ) -> BaselineRunSummary:
        """按水位增量聚合基线（celery 每日调度）。

        重要约束：
          - **不接受 bk_biz_ids 过滤**。同 rebuild，避免只处理部分业务导致全局基线口径失真。

        :param ticket_types: 限定单据类型；None 表示全部
        :return: BaselineRunSummary
        边界：
          - 首次运行且无水位记录：使用 INCREMENTAL_DEFAULT_LOOKBACK_DAYS 回溯
          - 水位表存在但 last_processed_finished_at 为空：同上
          - 每分片单独读水位、聚合、写水位；一个分片失败不影响其它
          - 会同步维护 bk_biz_id=0 全局基线
        """
        # 内部通道保留 bk_biz_ids（此处永远传 None）
        bk_biz_ids: Optional[List[int]] = None

        until: datetime = timezone.now()
        summary: BaselineRunSummary = BaselineRunSummary(
            mode=BaselineAggregator.MODE_INCREMENTAL, since=until, until=until  # since 会被分片各自覆盖
        )
        logger.info(
            "[FlowBaselineService] incremental_run start until=%s tt=%s",
            until,
            ticket_types,
        )

        # 增量场景需要按分片各自读水位 → 各自聚合 → 各自写水位
        earliest_since: Optional[datetime] = None
        for shard in self._iter_shards(bk_biz_ids, ticket_types, since=None, until=until):
            shard_since: datetime = self._read_watermark(shard.ticket_type, shard.bk_biz_id) or (
                self._collector.get_default_since(INCREMENTAL_DEFAULT_LOOKBACK_DAYS)
            )
            if shard_since >= until:
                # 水位已到 / 越过 until，无新数据可处理
                continue
            if earliest_since is None or shard_since < earliest_since:
                earliest_since = shard_since

            # 每个分片独立 aggregator，flush 完立刻清空
            aggregator: BaselineAggregator = BaselineAggregator(mode=BaselineAggregator.MODE_INCREMENTAL)
            global_aggregator: BaselineAggregator = BaselineAggregator(mode=BaselineAggregator.MODE_INCREMENTAL)

            self._process_shard(
                shard=shard,
                since=shard_since,
                until=until,
                aggregator=aggregator,
                global_aggregator=global_aggregator,
                summary=summary,
                dry_run=False,
            )

            written: int = aggregator.flush_to_db() + global_aggregator.flush_to_db()
            summary.buckets_written += written

            # 推进水位（即使 aggregator 无新样本，也更新 last_run_at 便于观测）
            self._write_watermark(
                shard.ticket_type,
                shard.bk_biz_id,
                last_processed_finished_at=until,
                last_run_sample_count=aggregator.observed_count,
            )

        # summary.since 用最早分片水位作为参考
        if earliest_since is not None:
            summary.since = earliest_since

        logger.info("[FlowBaselineService] incremental_run done, summary=%s", summary.as_dict())
        return summary

    # =========================================================================
    # 入口 3：定点修复（Command 修复入口）
    # =========================================================================

    def repair(
        self,
        bk_biz_ids: List[int],
        ticket_types: List[str],
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> BaselineRunSummary:
        """定点修复：仅重建指定 (bk_biz_ids × ticket_types) 的**业务级**基线。

        与 rebuild 的差异：
          - 允许（且强制要求）指定 bk_biz_ids，仅修复业务级基线
          - **完全跳过全局基线（bk_biz_id=0）**：既不清也不重建，避免因样本范围不全污染全局口径
          - 若需要重建全局基线，请用 rebuild()（rebuild 会全业务参与）

        :param bk_biz_ids: 必填；要修复的业务ID列表（不能包含 0；0 表示全局基线，禁止用 repair 触碰）
        :param ticket_types: 必填；要修复的单据类型列表
        :param since: 时间窗起点；None 使用 STOCK_DEFAULT_LOOKBACK_DAYS 回溯
        :param until: 时间窗终点；None 使用当前时间
        :return: BaselineRunSummary（mode='repair'）
        边界：
          - bk_biz_ids / ticket_types 任一为空 → 抛 ValueError（避免误全量清空）
          - bk_biz_ids 中若混入 0 → 抛 ValueError（0 是全局基线保留位，禁止 repair）
        """
        if not bk_biz_ids:
            raise ValueError("repair requires non-empty bk_biz_ids")
        if not ticket_types:
            raise ValueError("repair requires non-empty ticket_types")
        if GLOBAL_BASELINE_BK_BIZ_ID in bk_biz_ids:
            raise ValueError(
                f"repair must not include bk_biz_id={GLOBAL_BASELINE_BK_BIZ_ID} "
                f"(reserved for global baseline; use rebuild() to refresh it)"
            )

        summary: BaselineRunSummary = self._do_rebuild(
            bk_biz_ids=bk_biz_ids,
            ticket_types=ticket_types,
            since=since,
            until=until,
            dry_run=False,
            maintain_global=False,
            advance_watermarks=False,
        )
        summary.mode = "repair"
        return summary

    # =========================================================================
    # 内部：rebuild / repair 共用实现
    # =========================================================================

    def _do_rebuild(
        self,
        bk_biz_ids: Optional[List[int]],
        ticket_types: Optional[List[str]],
        since: Optional[datetime],
        until: Optional[datetime],
        dry_run: bool,
        maintain_global: bool,
        advance_watermarks: bool,
    ) -> BaselineRunSummary:
        """rebuild / repair 的公共底层实现。

        :param bk_biz_ids:
          - None 表示全量业务（rebuild 场景）
          - 非空 list 表示定点范围（repair 场景）
          - 保留该内部参数是为了未来若不再维护全局基线时，可低成本恢复"按业务过滤"的重建能力
        :param ticket_types: 单据类型过滤；None 表示全量
        :param since / until: 时间窗
        :param dry_run: 只统计不写库
        :param maintain_global: 是否维护 bk_biz_id=0 全局基线
          - True：清全局 + 累计全局 + flush 全局
          - False：完全跳过全局基线相关的所有操作（repair 语义）
        :param advance_watermarks: 是否在结束后推进业务级水位
          - True：rebuild 场景，覆盖式重建后需要把水位推到 until，避免下次 incremental 重复采样
          - False：repair 场景，绝对不能推进水位；否则 repair 会误将业务水位跳到 now，
            导致此后 incremental 漏采 [repair, incremental) 之间的样本
        :return: BaselineRunSummary
        """
        until = until or timezone.now()
        since = since or self._collector.get_default_since(STOCK_DEFAULT_LOOKBACK_DAYS)

        summary: BaselineRunSummary = BaselineRunSummary(
            mode=BaselineAggregator.MODE_REBUILD, since=since, until=until
        )
        logger.info(
            "[FlowBaselineService] rebuild start since=%s until=%s biz=%s tt=%s " "dry_run=%s maintain_global=%s",
            since,
            until,
            bk_biz_ids,
            ticket_types,
            dry_run,
            maintain_global,
        )

        # 1. 快照即将被删除行的 baseline_version（用于 rebuild/repair 覆写后延续版本号自增）
        #    - 业务级：受 bk_biz_ids × ticket_types 过滤范围影响
        #    - 全局：仅在 maintain_global=True 且 ticket_types 命中时快照
        biz_version_snapshot: Dict[Tuple[str, int, str, str], int] = {}
        global_version_snapshot: Dict[Tuple[str, int, str, str], int] = {}
        if not dry_run:
            biz_version_snapshot, global_version_snapshot = self._snapshot_baseline_versions(
                bk_biz_ids=bk_biz_ids,
                ticket_types=ticket_types,
                include_global=maintain_global,
            )

        # 2. 清空目标范围内已有基线（含或不含全局基线，取决于 maintain_global）
        if not dry_run:
            self._purge_baselines(bk_biz_ids, ticket_types, purge_global=maintain_global)

        # 3. 采样 + 归一化 + 聚合
        aggregator: BaselineAggregator = BaselineAggregator(mode=BaselineAggregator.MODE_REBUILD)
        aggregator.set_version_snapshot(biz_version_snapshot)
        global_aggregator: Optional[BaselineAggregator] = (
            BaselineAggregator(mode=BaselineAggregator.MODE_REBUILD) if maintain_global else None
        )
        if global_aggregator is not None:
            global_aggregator.set_version_snapshot(global_version_snapshot)

        # 分片并逐片处理，控制内存
        for shard in self._iter_shards(bk_biz_ids, ticket_types, since, until):
            self._process_shard(
                shard=shard,
                since=since,
                until=until,
                aggregator=aggregator,
                global_aggregator=global_aggregator,
                summary=summary,
                dry_run=dry_run,
            )

        # 4. flush 剩余（若走的是"多分片单 aggregator"路径，前面已 flush 过；此处兜底）
        if not dry_run:
            summary.buckets_written += aggregator.flush_to_db()
            if global_aggregator is not None:
                summary.buckets_written += global_aggregator.flush_to_db()

        # 5. 更新水位（仅 rebuild 场景；repair 绝对不推进水位，以免 incremental 漏采）
        if not dry_run and advance_watermarks:
            self._advance_watermarks(bk_biz_ids, ticket_types, until, summary.samples_accumulated)

        logger.info("[FlowBaselineService] rebuild done, summary=%s", summary.as_dict())
        return summary

    # =========================================================================
    # 内部：分片处理
    # =========================================================================

    def _process_shard(
        self,
        shard: "_Shard",
        since: datetime,
        until: datetime,
        aggregator: BaselineAggregator,
        global_aggregator: Optional[BaselineAggregator],
        summary: BaselineRunSummary,
        dry_run: bool,
    ) -> None:
        """处理单个 (ticket_type, bk_biz_id) 分片。

        流程：
          1. Collector 拉取本分片样本
          2. Normalizer 归一化
          3. Aggregator 累计
          4. Global aggregator 累计（仅当 global_aggregator 非空时执行；bk_biz_id 强制置 0）
          5. 分片处理完 → 清 Normalizer 内存缓存

        :param shard: (ticket_type, bk_biz_id) 分片描述
        :param aggregator: 业务级 aggregator
        :param global_aggregator: 全局 aggregator（写入时把 bk_biz_id 强制置 0）；
                                  None 表示当前调用不需要维护全局基线（例如 repair 场景）
        """
        try:
            for sample in self._collector.iter_samples(
                since=since,
                until=until,
                bk_biz_ids=[shard.bk_biz_id],
                ticket_types=[shard.ticket_type],
            ):
                summary.samples_collected += 1

                normalized_name: str = self._normalizer.normalize(
                    ticket_type=sample.ticket_type,
                    component_code=sample.component_code,
                    raw_name=sample.raw_name,
                ).normalized_name

                if not normalized_name:
                    continue

                aggregator.accumulate(sample, normalized_name)

                # 全局基线：仅在需要维护时（rebuild / incremental 场景）累计
                if global_aggregator is not None:
                    global_sample: NodeDurationSample = self._as_global_sample(sample)
                    global_aggregator.accumulate(global_sample, normalized_name)

                summary.samples_accumulated += 1

                # 内存超阈值触发 flush（仅 rebuild 场景需要防膨胀）
                if not dry_run and aggregator.observed_count >= self._FLUSH_THRESHOLD_SAMPLES:
                    summary.buckets_written += aggregator.flush_to_db()
                    if global_aggregator is not None:
                        summary.buckets_written += global_aggregator.flush_to_db()

            summary.shards_processed += 1
        except Exception as err:
            logger.exception(
                "[FlowBaselineService] process shard failed, tt=%s biz=%s err=%s",
                shard.ticket_type,
                shard.bk_biz_id,
                err,
            )
            summary.failures.append((shard.ticket_type, shard.bk_biz_id, str(err)))
        finally:
            # 每个分片处理完，清一次 Normalizer 内存缓存，控制内存膨胀
            self._normalizer.clear_cache()

    @staticmethod
    def _as_global_sample(sample: NodeDurationSample) -> NodeDurationSample:
        """把样本的 bk_biz_id 覆盖为全局基线占位值 0；其它字段不变。"""
        return NodeDurationSample(
            ticket_type=sample.ticket_type,
            bk_biz_id=GLOBAL_BASELINE_BK_BIZ_ID,
            component_code=sample.component_code,
            raw_name=sample.raw_name,
            duration_seconds=sample.duration_seconds,
            finished_at=sample.finished_at,
            root_id=sample.root_id,
            node_id=sample.node_id,
        )

    # =========================================================================
    # 内部：分片枚举
    # =========================================================================

    def _iter_shards(
        self,
        bk_biz_ids: Optional[List[int]],
        ticket_types: Optional[List[str]],
        since: Optional[datetime],
        until: datetime,
    ) -> Iterator["_Shard"]:
        """枚举待处理的 (ticket_type, bk_biz_id) 分片。

        分片来源（优先级从高到低）：
          1. 用户显式传入的 bk_biz_ids × ticket_types 笛卡尔积
          2. 若用户未指定，从时间窗内的 FlowTree 里取 distinct (ticket_type, bk_biz_id)
        """
        if bk_biz_ids and ticket_types:
            for tt in ticket_types:
                for biz in bk_biz_ids:
                    yield _Shard(ticket_type=tt, bk_biz_id=biz)
            return

        # 从 FlowTree 取 distinct 分片
        from backend.flow.consts import StateType
        from backend.flow.models import FlowTree

        qs = FlowTree.objects.filter(status=StateType.FINISHED.value)
        if since is not None:
            qs = qs.filter(updated_at__gte=since)
        qs = qs.filter(updated_at__lt=until)
        if bk_biz_ids:
            qs = qs.filter(bk_biz_id__in=bk_biz_ids)
        if ticket_types:
            qs = qs.filter(ticket_type__in=ticket_types)

        distinct_pairs: Set[Tuple[str, int]] = set()
        for tt, biz in qs.values_list("ticket_type", "bk_biz_id").distinct().iterator(chunk_size=500):
            if not tt:
                continue
            distinct_pairs.add((tt, int(biz or 0)))

        # 稳定顺序：先按 ticket_type 后按 biz_id 排序，便于日志可追溯
        for tt, biz in sorted(distinct_pairs):
            yield _Shard(ticket_type=tt, bk_biz_id=biz)

    # =========================================================================
    # 内部：baseline 表清理
    # =========================================================================

    def _purge_baselines(
        self,
        bk_biz_ids: Optional[List[int]],
        ticket_types: Optional[List[str]],
        purge_global: bool = True,
    ) -> None:
        """清空指定范围的 FlowNodeDurationBaseline 记录。

        :param bk_biz_ids: 业务过滤；None 表示全部业务
        :param ticket_types: 单据类型过滤；None 表示全部单据类型
        :param purge_global: 是否连同 bk_biz_id=0 全局基线一并清空
          - True（默认）：rebuild 场景，需要重建全局基线，先清后重建
          - False：repair 场景，绝对不动全局基线

        安全约束：
          - 至少要提供 bk_biz_ids 或 ticket_types 之一，否则会拒绝执行（避免误清全表）
          - 全局基线 (bk_biz_id=0) 只在 purge_global=True 且 ticket_types 命中时清理
        """
        if not bk_biz_ids and not ticket_types:
            logger.warning(
                "[FlowBaselineService] refuse to purge without any filter; use full rebuild via explicit args"
            )
            return

        with transaction.atomic(using="report_db"):
            # 业务级 baseline
            biz_qs = FlowNodeDurationBaseline.objects.all()
            if bk_biz_ids:
                biz_qs = biz_qs.filter(bk_biz_id__in=bk_biz_ids)
            else:
                # 未指定业务：清所有业务级（排除全局占位 0），避免与全局基线清理策略混淆
                biz_qs = biz_qs.exclude(bk_biz_id=GLOBAL_BASELINE_BK_BIZ_ID)
            if ticket_types:
                biz_qs = biz_qs.filter(ticket_type__in=ticket_types)
            deleted_biz, _ = biz_qs.delete()

            # 全局 baseline：仅在 purge_global=True 且 ticket_types 命中时清理
            deleted_global: int = 0
            if purge_global and ticket_types:
                global_qs = FlowNodeDurationBaseline.objects.filter(
                    bk_biz_id=GLOBAL_BASELINE_BK_BIZ_ID, ticket_type__in=ticket_types
                )
                deleted_global, _ = global_qs.delete()

        logger.info(
            "[FlowBaselineService] purge done, deleted_biz=%d deleted_global=%d purge_global=%s",
            deleted_biz,
            deleted_global,
            purge_global,
        )

    def _snapshot_baseline_versions(
        self,
        bk_biz_ids: Optional[List[int]],
        ticket_types: Optional[List[str]],
        include_global: bool,
    ) -> Tuple[Dict[Tuple[str, int, str, str], int], Dict[Tuple[str, int, str, str], int]]:
        """在 purge 前把即将被删除的行的 baseline_version 快照下来，供 rebuild/repair
        重写时延续版本号自增（old_version + 1）。

        返回两张字典：
          - biz_snapshot：业务级基线（bk_biz_id != 0）的 (4 元组 -> 老 baseline_version)
          - global_snapshot：全局基线（bk_biz_id == 0）的 (4 元组 -> 老 baseline_version)
            仅当 include_global=True 且 ticket_types 命中时才有值；否则空 dict

        :param bk_biz_ids: 与 _purge_baselines 保持一致的业务过滤条件
        :param ticket_types: 与 _purge_baselines 保持一致的单据类型过滤条件
        :param include_global: 是否一并快照全局基线（仅 rebuild 需要，repair 场景传 False）
        :return: (biz_snapshot, global_snapshot)
        边界：
          - 若过滤范围为空（bk_biz_ids 与 ticket_types 均为 None）：与 _purge_baselines 拒绝行为对齐，
            此时仍会读取全部业务级行的版本号，用于全量 rebuild 的场景
        """
        biz_snapshot: Dict[Tuple[str, int, str, str], int] = {}
        global_snapshot: Dict[Tuple[str, int, str, str], int] = {}

        # 业务级快照（排除全局占位 0）
        biz_qs = FlowNodeDurationBaseline.objects.all()
        if bk_biz_ids:
            biz_qs = biz_qs.filter(bk_biz_id__in=bk_biz_ids)
        else:
            biz_qs = biz_qs.exclude(bk_biz_id=GLOBAL_BASELINE_BK_BIZ_ID)
        if ticket_types:
            biz_qs = biz_qs.filter(ticket_type__in=ticket_types)

        for tt, biz, code, name, ver in biz_qs.values_list(
            "ticket_type", "bk_biz_id", "component_code", "normalized_name", "baseline_version"
        ).iterator(chunk_size=1000):
            biz_snapshot[(tt, int(biz or 0), code, name)] = int(ver or 1)

        # 全局快照（仅 rebuild 需要）
        if include_global and ticket_types:
            global_qs = FlowNodeDurationBaseline.objects.filter(
                bk_biz_id=GLOBAL_BASELINE_BK_BIZ_ID, ticket_type__in=ticket_types
            )
            for tt, biz, code, name, ver in global_qs.values_list(
                "ticket_type", "bk_biz_id", "component_code", "normalized_name", "baseline_version"
            ).iterator(chunk_size=1000):
                global_snapshot[(tt, int(biz or 0), code, name)] = int(ver or 1)

        logger.info(
            "[FlowBaselineService] snapshot baseline_version, biz=%d global=%d",
            len(biz_snapshot),
            len(global_snapshot),
        )
        return biz_snapshot, global_snapshot

    # =========================================================================
    # 内部：水位读写
    # =========================================================================

    def _read_watermark(self, ticket_type: str, bk_biz_id: int) -> Optional[datetime]:
        """读取 (ticket_type, bk_biz_id) 的水位；不存在返回 None。"""
        row: Optional[FlowNodeBaselineWatermark] = (
            FlowNodeBaselineWatermark.objects.filter(ticket_type=ticket_type, bk_biz_id=bk_biz_id)
            .only("last_processed_finished_at")
            .first()
        )
        return row.last_processed_finished_at if row else None

    def _write_watermark(
        self,
        ticket_type: str,
        bk_biz_id: int,
        last_processed_finished_at: datetime,
        last_run_sample_count: int,
    ) -> None:
        """upsert 水位记录。"""
        with transaction.atomic(using="report_db"):
            FlowNodeBaselineWatermark.objects.update_or_create(
                ticket_type=ticket_type,
                bk_biz_id=bk_biz_id,
                defaults={
                    "last_processed_finished_at": last_processed_finished_at,
                    "last_run_at": timezone.now(),
                    "last_run_sample_count": last_run_sample_count,
                },
            )

    def _advance_watermarks(
        self,
        bk_biz_ids: Optional[List[int]],
        ticket_types: Optional[List[str]],
        until: datetime,
        total_samples: int,
    ) -> None:
        """rebuild 完成后批量推进水位。

        规则：
          - 只对本次 rebuild 覆盖到的分片推进水位
          - 若 bk_biz_ids / ticket_types 均为 None（全量重建），则从数据库枚举实际存在的分片
        """
        pairs: List[Tuple[str, int]] = []

        if bk_biz_ids and ticket_types:
            pairs = [(tt, biz) for tt in ticket_types for biz in bk_biz_ids]
        else:
            # 从 baseline 表枚举本次 rebuild 覆盖的分片
            baseline_qs = FlowNodeDurationBaseline.objects.all()
            if bk_biz_ids:
                baseline_qs = baseline_qs.filter(bk_biz_id__in=bk_biz_ids)
            if ticket_types:
                baseline_qs = baseline_qs.filter(ticket_type__in=ticket_types)
            for tt, biz in baseline_qs.values_list("ticket_type", "bk_biz_id").distinct().iterator(chunk_size=500):
                pairs.append((tt, int(biz or 0)))

        # 平摊 total_samples 到各分片仅供观测；实际值不精确
        avg_samples: int = int(total_samples / max(len(pairs), 1))
        for tt, biz in pairs:
            if biz == GLOBAL_BASELINE_BK_BIZ_ID:
                # 全局基线不需要独立水位，跳过
                continue
            try:
                self._write_watermark(tt, biz, until, avg_samples)
            except Exception as err:
                logger.warning("[FlowBaselineService] advance watermark failed, tt=%s biz=%s err=%s", tt, biz, err)


@dataclass(frozen=True)
class _Shard:
    """(ticket_type, bk_biz_id) 分片描述；仅供 FlowBaselineService 内部使用。"""

    ticket_type: str
    bk_biz_id: int
