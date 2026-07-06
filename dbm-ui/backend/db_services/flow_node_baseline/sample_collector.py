# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

FlowSampleCollector：flow_tree / flow_node 的耗时样本采集器。

模块职责：
  - 按时间窗 + biz_id + ticket_type 过滤扫描 flow_tree
  - 递归解析 flow_tree.tree JSON，提取每个 ServiceActivity 节点的 (component_code, component_name)
  - 关联 flow_node 表读取节点耗时数据（updated_at - started_at）
  - 应用 SAMPLE_MIN/MAX_DURATION_SECONDS 过滤异常样本（真实 delta 先经 math.ceil 向上取整）
  - 命中 EXCLUDED_COMPONENT_CODES 的节点静默跳过（人工暂停节点，天然超长耗时）
  - 越界样本（delta<0 视为时钟回拨 / >24h 视为悬挂）落 FlowNodeSampleReject 供 DBA 排查
  - 以生成器方式流式吐出 NodeDurationSample，避免一次性加载所有样本到内存

上下游边界：
  - 上游：FlowBaselineService（存量/增量共用），传入过滤条件
  - 下游：BaselineAggregator 消费样本流做增量聚合；FlowNodeSampleReject 表由本模块直接写入

数据源：
  - backend.flow.models.FlowTree（default 库）
  - backend.flow.models.FlowNode（default 库）
写入：
  - backend.db_report.models.FlowNodeSampleReject（report_db 库；只写"耗时越界"档案）
"""
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterator, List, Optional, Tuple

from django.utils import timezone

from backend.db_report.models import FlowNodeSampleReject, RejectReason
from backend.db_services.flow_node_baseline.constants import (
    EXCLUDED_COMPONENT_CODES,
    FLOW_NODE_ITER_CHUNK_SIZE,
    FLOW_TREE_ITER_CHUNK_SIZE,
    REJECT_SAMPLE_FLUSH_BATCH_SIZE,
    SAMPLE_MAX_DURATION_SECONDS,
    SAMPLE_MIN_DURATION_SECONDS,
    STOCK_TASK_SLICE_DAYS,
)
from backend.flow.consts import StateType
from backend.flow.models import FlowNode, FlowTree

logger = logging.getLogger("root")


@dataclass(frozen=True)
class NodeDurationSample:
    """单条节点耗时样本；下游 BaselineAggregator 的最小消费单元。

    :ivar ticket_type: 单据类型（来自 FlowTree.ticket_type）
    :ivar bk_biz_id: 业务ID（来自 FlowTree.bk_biz_id）
    :ivar component_code: 组件代码（来自 tree.activities[node_id].component.code）
    :ivar raw_name: 原始节点名称（来自 tree.activities[node_id].name），未清洗
    :ivar duration_seconds: 节点耗时（秒），已通过上下界过滤
    :ivar finished_at: 节点完成时间（= FlowNode.updated_at），供水位推进使用
    :ivar root_id: 所属 flow 的 root_id，供追踪与去重
    :ivar node_id: 节点 ID，供追踪
    """

    ticket_type: str
    bk_biz_id: int
    component_code: str
    raw_name: str
    duration_seconds: int
    finished_at: datetime
    root_id: str
    node_id: str


class _FlowTreeParser:
    """解析 FlowTree.tree JSON，递归展开 activities → {node_id: (code, name)}。

    职责：
      - 支持 ServiceActivity（叶子节点，产生样本）
      - 支持 SubProcess（子流程，需递归展开其 pipeline.activities）
      - 忽略 ParallelGateway / ExclusiveGateway 等不产生耗时样本的节点

    使用方式：
        node_map = _FlowTreeParser.extract(flow_tree.tree)
        # node_map = {"node_id_1": ("mysql_db_actuator_execute", "分区优化执行"), ...}

    线程安全：是（无实例状态；类方法风格）
    边界：
      - tree 为 None / 空 dict → 返回空 dict
      - activity 缺少 component 字段 → 该节点跳过
      - SubProcess 无 pipeline → 视为空子流程跳过
    """

    _TYPE_SERVICE_ACTIVITY: str = "ServiceActivity"
    _TYPE_SUBPROCESS: str = "SubProcess"

    @classmethod
    def extract(cls, tree: Optional[Dict]) -> Dict[str, Tuple[str, str]]:
        """展开 tree 中所有 ServiceActivity。

        :param tree: FlowTree.tree 原始 JSON
        :return: {node_id: (component_code, component_name)}；空/异常返回空 dict
        边界：见类 docstring
        """
        result: Dict[str, Tuple[str, str]] = {}
        if not tree:
            return result
        activities: Dict = tree.get("activities") or {}
        cls._walk(activities, result)
        return result

    @classmethod
    def _walk(cls, activities: Dict, result: Dict[str, Tuple[str, str]]) -> None:
        """递归遍历 activities 字典。"""
        for node_id, activity in activities.items():
            if not isinstance(activity, dict):
                continue
            act_type: str = activity.get("type", "")
            if act_type == cls._TYPE_SERVICE_ACTIVITY:
                component: Dict = activity.get("component") or {}
                code: str = component.get("code", "") or ""
                name: str = activity.get("name", "") or ""
                result[node_id] = (code, name)
            elif act_type == cls._TYPE_SUBPROCESS:
                sub_pipeline: Dict = activity.get("pipeline") or {}
                sub_activities: Dict = sub_pipeline.get("activities") or {}
                if sub_activities:
                    cls._walk(sub_activities, result)


class FlowSampleCollector:
    """flow 节点耗时样本采集器（存量/增量共用）。

    职责：
      - 按 (since, until, bk_biz_ids, ticket_types) 条件扫描 FlowTree
      - 对每个 flow 解析 tree + 关联 FlowNode 计算单节点耗时
      - 通过样本上下界过滤异常样本，流式吐出合法样本
      - 命中 EXCLUDED_COMPONENT_CODES 的节点静默跳过（既不入基线也不入 reject）
      - 越界样本落 FlowNodeSampleReject 供 DBA 事后排查

    使用方式：
        collector = FlowSampleCollector()
        for sample in collector.iter_samples(since=..., until=..., bk_biz_ids=[591]):
            aggregator.accumulate(sample)

    线程安全：不是（内部维护 _reject_buffer 缓冲区，一个采集实例只应在一个线程/协程使用）
    副作用：只读 flow_tree / flow_node；写 FlowNodeSampleReject（越界样本档案）
    边界：
      - since >= until → 直接返回空迭代器
      - flow.tree 为空 / activities 为空 → 跳过整个 flow
      - node.started_at 为空 → 跳过该 node（引擎异常场景）
      - component_code 命中黑名单 → 静默跳过（如 pause 节点）
      - duration < SAMPLE_MIN 或 > SAMPLE_MAX → 落 reject 表并跳过
    """

    #: 处理的 flow 状态白名单：只统计已完成流程；失败/撤销流程的耗时不入基线
    _ALLOWED_FLOW_STATUS: List[str] = [StateType.FINISHED.value]

    #: 处理的 node 状态白名单：只统计成功完成的节点
    _ALLOWED_NODE_STATUS: List[str] = [StateType.FINISHED.value]

    def __init__(self) -> None:
        """初始化 reject 缓冲区与静默丢弃计数器。

        - reject 缓冲区：保存尚未落库的 FlowNodeSampleReject 实例；
          每积累到 REJECT_SAMPLE_FLUSH_BATCH_SIZE 或采集结束时统一 flush。
        - 静默丢弃计数器：本模块存在多个"静默跳过"路径（既不入基线也不入 reject），
          若不做统计，一旦某个 component_code 的样本"整体消失"，DBA 无法定位是被哪一层
          过滤掉的。这里按 stage 累计计数，采集结束时打点日志便于排障。
          key 命名与代码里的过滤位置一一对应，改动过滤逻辑时请同步维护。
        """
        self._reject_buffer: List[FlowNodeSampleReject] = []

        #: 静默丢弃计数：{stage_key: count}
        #: stage_key 定义（覆盖所有静默跳过点）：
        #:   - tree_empty            : FlowTree.tree 为空 / 无 activities
        #:   - excluded_by_code_black: component_code 命中 EXCLUDED_COMPONENT_CODES 黑名单
        #:   - node_time_null        : FlowNode.started_at 或 updated_at 为空
        #:   - label_missing         : node_id 未出现在 tree 解析结果里（引擎/tree 不一致）
        #:   - empty_component_code  : tree 里该 activity 的 component.code 为空
        #: 每次 iter_samples() 调用会重置此计数器。
        self._drop_counter: Dict[str, int] = {}

    def iter_samples(
        self,
        since: datetime,
        until: datetime,
        bk_biz_ids: Optional[List[int]] = None,
        ticket_types: Optional[List[str]] = None,
    ) -> Iterator[NodeDurationSample]:
        """按条件流式产出耗时样本（生成器）。

        :param since: 时间窗起点（含）；基于 FlowTree.updated_at（流程结束时间）
        :param until: 时间窗终点（不含）
        :param bk_biz_ids: 业务ID过滤；None 表示不限
        :param ticket_types: 单据类型过滤；None 表示不限
        :return: 生成器，每次 yield 一个 NodeDurationSample
        边界：
          - since >= until → 立即返回，不产生任何样本
          - 内部按天切片，规避单条 SQL 拉取过多 flow 导致的慢查询
          - 单个 flow 处理失败仅告警，不中断整个采集
          - 生成器被 close/正常耗尽时，reject 缓冲区通过 finally 统一 flush
        """
        if since >= until:
            logger.warning("[FlowSampleCollector] invalid time range: since=%s until=%s", since, until)
            return

        # 每次采集重置计数器；避免跨调用累积干扰观测
        self._drop_counter = {}

        try:
            for slice_start, slice_end in self._make_time_slices(since, until):
                yield from self._iter_slice(slice_start, slice_end, bk_biz_ids, ticket_types)
        finally:
            # 无论正常结束、上层 break、还是抛异常，都保证 reject 缓冲落库
            self._flush_rejects(force=True)
            # 采集结束时打点静默丢弃统计，方便 DBA 定位"某 code 样本整体消失"类问题
            if self._drop_counter:
                logger.info(
                    "[FlowSampleCollector] silent drop stats since=%s until=%s stats=%s",
                    since,
                    until,
                    dict(self._drop_counter),
                )

    # =========================================================================
    # 内部：切片扫描
    # =========================================================================
    @staticmethod
    def _make_time_slices(since: datetime, until: datetime) -> Iterator[Tuple[datetime, datetime]]:
        """将 [since, until] 按 STOCK_TASK_SLICE_DAYS 切片，避免单条 SQL 拉取过多。

        :yield: (slice_start, slice_end) 元组，左闭右开
        """
        cursor: datetime = since
        step: timedelta = timedelta(days=STOCK_TASK_SLICE_DAYS)
        while cursor < until:
            end: datetime = min(cursor + step, until)
            yield cursor, end
            cursor = end

    def _iter_slice(
        self,
        slice_start: datetime,
        slice_end: datetime,
        bk_biz_ids: Optional[List[int]],
        ticket_types: Optional[List[str]],
    ) -> Iterator[NodeDurationSample]:
        """处理单个时间切片：扫 flow_tree + 关联 flow_node。"""
        flow_qs = FlowTree.objects.filter(
            status__in=self._ALLOWED_FLOW_STATUS,
            updated_at__gte=slice_start,
            updated_at__lt=slice_end,
        ).only("root_id", "bk_biz_id", "ticket_type", "tree")

        if bk_biz_ids:
            flow_qs = flow_qs.filter(bk_biz_id__in=bk_biz_ids)
        if ticket_types:
            flow_qs = flow_qs.filter(ticket_type__in=ticket_types)

        for flow_tree in flow_qs.iterator(chunk_size=FLOW_TREE_ITER_CHUNK_SIZE):
            try:
                yield from self._iter_flow(flow_tree)
            except Exception as err:
                # 单个 flow 失败不中断整体采集；仅告警
                logger.warning(
                    "[FlowSampleCollector] parse flow failed, root_id=%s err=%s",
                    getattr(flow_tree, "root_id", "?"),
                    err,
                )

    def _iter_flow(self, flow_tree: FlowTree) -> Iterator[NodeDurationSample]:
        """处理单个 flow：解析 tree → 剔除黑名单节点 → 关联 flow_node → 逐节点吐样本。

        为节省 DB 查询与内存，本方法在关联 FlowNode 之前先剔除掉所有命中
        EXCLUDED_COMPONENT_CODES 的节点（如 pause），避免把明显不需要的节点也捞出来。
        """
        node_label_map: Dict[str, Tuple[str, str]] = _FlowTreeParser.extract(flow_tree.tree)
        if not node_label_map:
            # tree 为空 / 无 activities：静默跳过并计数
            self._drop_counter["tree_empty"] = self._drop_counter.get("tree_empty", 0) + 1
            return

        # 提前剔除 code 黑名单节点：静默跳过，不参与后续查询、也不入 reject
        effective_label_map: Dict[str, Tuple[str, str]] = {}
        excluded_count: int = 0
        for node_id, label in node_label_map.items():
            if label[0] in EXCLUDED_COMPONENT_CODES:
                excluded_count += 1
                continue
            effective_label_map[node_id] = label
        if excluded_count:
            self._drop_counter["excluded_by_code_black"] = (
                self._drop_counter.get("excluded_by_code_black", 0) + excluded_count
            )
        if not effective_label_map:
            return

        # 只查这批 node_id、只取时间字段，减少回表
        nodes_qs = FlowNode.objects.filter(
            root_id=flow_tree.root_id,
            status__in=self._ALLOWED_NODE_STATUS,
            node_id__in=list(effective_label_map.keys()),
            started_at__isnull=False,
            updated_at__isnull=False,
        ).only("node_id", "started_at", "updated_at")

        ticket_type: str = flow_tree.ticket_type or ""
        bk_biz_id: int = flow_tree.bk_biz_id or 0

        for node in nodes_qs.iterator(chunk_size=FLOW_NODE_ITER_CHUNK_SIZE):
            sample: Optional[NodeDurationSample] = self._build_sample(
                node, effective_label_map, ticket_type, bk_biz_id, flow_tree.root_id
            )
            if sample is not None:
                yield sample

    # =========================================================================
    # 【核心】耗时计算 —— 请重点核对本方法
    # =========================================================================

    def _build_sample(
        self,
        node: FlowNode,
        node_label_map: Dict[str, Tuple[str, str]],
        ticket_type: str,
        bk_biz_id: int,
        root_id: str,
    ) -> Optional[NodeDurationSample]:
        """构造单条耗时样本；此处集中封装耗时计算与过滤逻辑。

        过滤链（按顺序）：
          1. 时间字段兜底：started_at / updated_at 为空 → 静默跳过
          2. label 兜底：node_id 不在 label_map、component_code 空 → 静默跳过
             （黑名单节点在 _iter_flow 已提前剔除，此处只做防御）
          3. 耗时计算：duration_seconds = math.ceil((updated_at - started_at).total_seconds())
             说明：FlowNode.updated_at 是 auto_now=True 字段，节点每次状态变更都会刷新；
                   对已 FINISHED 的节点，updated_at 即"最后一次变为 FINISHED 的时间"。
                   FlowNode.started_at 由引擎在节点开始执行时显式写入。
                   使用 math.ceil 向上取整，让亚秒真实节点（如 sqlserver_add_job_user 0.2~0.6s）
                   最小对齐到 1 秒后正常入基线，不再因 int() 硬切成 0 被下界丢弃。
          4. 耗时下界：delta < 0 → duration=0，记 TOO_SHORT 到 reject 表（时钟回拨）
          5. 耗时上界：duration > SAMPLE_MAX_DURATION_SECONDS → 记 TOO_LONG 到 reject 表

        :param node: FlowNode 实例；调用方保证 status=FINISHED 且时间字段非空
        :param node_label_map: 由 tree 解析并已剔除黑名单后的 {node_id: (code, name)} 映射
        :param ticket_type: 已从 flow_tree 取出的单据类型
        :param bk_biz_id: 已从 flow_tree 取出的业务ID
        :param root_id: 所属 flow 的 root_id
        :return: NodeDurationSample；不合法返回 None（越界样本已顺带落 reject）
        边界：见"过滤链"
        """
        # 1. 时间字段兜底校验（QuerySet 已过滤 isnull，此处防御式编程）
        if node.started_at is None or node.updated_at is None:
            self._drop_counter["node_time_null"] = self._drop_counter.get("node_time_null", 0) + 1
            return None

        # 2. 提前取 label 用于 reject 记录（拿不到就整体跳过）
        label: Optional[Tuple[str, str]] = node_label_map.get(node.node_id)
        if label is None:
            self._drop_counter["label_missing"] = self._drop_counter.get("label_missing", 0) + 1
            return None
        component_code, raw_name = label
        if not component_code:
            # 没有 component_code 无法作为四维 key，也无法归类到 reject
            self._drop_counter["empty_component_code"] = self._drop_counter.get("empty_component_code", 0) + 1
            return None

        # 3. 计算耗时（秒）
        # 使用 total_seconds() 可正确处理跨时区、夏令时等场景。
        # 精度处理：亚秒级真实节点（如 sqlserver_add_job_user 通常 0.2~0.6s）也是有效样本，
        #          用 math.ceil 向上取整而非 int() 硬切向下，避免这类节点整批被下界过滤丢弃；
        #          任何 delta > 0 的节点最小都会被拉齐为 1 秒。
        # 时钟回拨防御：ceil(-0.3) = 0，会绕过 <1 的下界；因此必须先用原始 delta 判负，
        #             负值直接按 0 秒记 reject，不进入 ceil 分支。
        delta_seconds: float = (node.updated_at - node.started_at).total_seconds()
        if delta_seconds < 0:
            # 时钟回拨：duration 记 0（低于 SAMPLE_MIN_DURATION_SECONDS=1，走 TOO_SHORT）
            duration_seconds: int = 0
        else:
            duration_seconds = int(math.ceil(delta_seconds))

        # 4. 耗时下界过滤（< SAMPLE_MIN_DURATION_SECONDS 视为时钟回拨）—— 记 reject 后跳过
        # 说明：正常节点经 ceil 后恒 >= 1，只有 delta < 0 分支写入的 0 才会命中此处。
        if duration_seconds < SAMPLE_MIN_DURATION_SECONDS:
            self._record_reject(
                node=node,
                root_id=root_id,
                bk_biz_id=bk_biz_id,
                ticket_type=ticket_type,
                component_code=component_code,
                raw_name=raw_name,
                duration_seconds=duration_seconds,
                reason=RejectReason.TOO_SHORT.value,
            )
            return None

        # 5. 耗时上界过滤（>24h 视为节点悬挂/异常）—— 记 reject 后跳过
        if duration_seconds > SAMPLE_MAX_DURATION_SECONDS:
            self._record_reject(
                node=node,
                root_id=root_id,
                bk_biz_id=bk_biz_id,
                ticket_type=ticket_type,
                component_code=component_code,
                raw_name=raw_name,
                duration_seconds=duration_seconds,
                reason=RejectReason.TOO_LONG.value,
            )
            return None

        return NodeDurationSample(
            ticket_type=ticket_type,
            bk_biz_id=bk_biz_id,
            component_code=component_code,
            raw_name=raw_name,
            duration_seconds=duration_seconds,
            finished_at=node.updated_at,
            root_id=root_id,
            node_id=node.node_id,
        )

    # =========================================================================
    # 内部：reject 缓冲与落库
    # =========================================================================

    def _record_reject(
        self,
        node: FlowNode,
        root_id: str,
        bk_biz_id: int,
        ticket_type: str,
        component_code: str,
        raw_name: str,
        duration_seconds: int,
        reason: str,
    ) -> None:
        """把一条越界样本追加到 reject 缓冲区；缓冲区达到批量阈值时自动 flush。

        :param node: 原始 FlowNode 实例（用于取 started_at / updated_at）
        :param root_id: flow root_id
        :param bk_biz_id: 业务 ID
        :param ticket_type: 单据类型
        :param component_code: 组件 code
        :param raw_name: 原始名称
        :param duration_seconds: 原始耗时（秒），照实存储不截断
        :param reason: RejectReason.value（"too_short" / "too_long"）
        """
        self._reject_buffer.append(
            FlowNodeSampleReject(
                root_id=root_id,
                node_id=node.node_id,
                bk_biz_id=bk_biz_id,
                ticket_type=ticket_type,
                component_code=component_code,
                raw_name=raw_name or "",
                duration_seconds=duration_seconds,
                started_at=node.started_at,
                finished_at=node.updated_at,
                reject_reason=reason,
            )
        )
        if len(self._reject_buffer) >= REJECT_SAMPLE_FLUSH_BATCH_SIZE:
            self._flush_rejects(force=False)

    def _flush_rejects(self, force: bool) -> None:
        """把 reject 缓冲区批量落库；同一 (root_id, node_id) 走 upsert 覆盖旧记录。

        :param force: True 表示无论缓冲区是否达到批量阈值都 flush（用于收尾）
        """
        if not self._reject_buffer:
            return
        if not force and len(self._reject_buffer) < REJECT_SAMPLE_FLUSH_BATCH_SIZE:
            return

        pending: List[FlowNodeSampleReject] = self._reject_buffer
        self._reject_buffer = []
        try:
            # Django 4.1+ 支持 update_conflicts 走 UPSERT 语义；
            # 同一 (root_id, node_id) 走覆盖更新，避免历史 rebuild 遗留脏数据。
            #
            # 兼容性注意（踩坑记录）：
            #   1. 蓝鲸 AuditedModel 更新时间字段名为 update_at（无 d），auto_now=True；
            #      bulk_create(update_conflicts=True) 不会自动刷新 auto_now 字段，
            #      必须显式写在 update_fields 里，UPSERT 分支才会重算写入。
            #   2. MySQL/MariaDB 后端不支持传 unique_fields
            #      （报 NotSupportedError: This database backend does not support
            #       updating conflicts with specifying unique fields ...）；
            #      MySQL 生成的是 INSERT ... ON DUPLICATE KEY UPDATE，语法上无法指定
            #      "特定唯一键"，会自动按表上所有 UNIQUE 索引匹配。本表只有一条唯一键
            #      (root_id, node_id)，因此不传 unique_fields 效果完全等价。
            #      如果未来切换到 PostGreSQL，需要重新加回 unique_fields。
            FlowNodeSampleReject.objects.bulk_create(
                pending,
                batch_size=REJECT_SAMPLE_FLUSH_BATCH_SIZE,
                update_conflicts=True,
                update_fields=[
                    "bk_biz_id",
                    "ticket_type",
                    "component_code",
                    "raw_name",
                    "duration_seconds",
                    "started_at",
                    "finished_at",
                    "reject_reason",
                    "updater",
                    "update_at",
                ],
            )
        except Exception as err:
            # reject 表的落库失败不能影响主基线流程；仅打 exception 便于定位根因
            # 打 exception 级别（含 traceback），否则字段名笔误、后端不兼容等结构性错误
            # 只能看到一行 warning，无法快速定位。
            logger.exception(
                "[FlowSampleCollector] flush reject buffer failed, size=%d err=%s",
                len(pending),
                err,
            )

    # =========================================================================
    # 辅助方法：给 FlowBaselineService 用于水位推进
    # =========================================================================
    @staticmethod
    def get_default_since(lookback_days: int) -> datetime:
        """基于当前时间计算默认 since；用于首次运行无水位场景。

        :param lookback_days: 回溯天数
        :return: 当前时间 - lookback_days
        """
        return timezone.now() - timedelta(days=lookback_days)
