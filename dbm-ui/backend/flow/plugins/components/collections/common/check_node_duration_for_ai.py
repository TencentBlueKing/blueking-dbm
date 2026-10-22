# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

单据值守 · 节点耗时超线提醒 sidecar。

模块职责：
  - 周期性扫描当前 flow 中所有正在运行的 ServiceActivity 节点，计算每个节点的已运行耗时
  - 把已耗时与 `FlowNodeDurationBaseline`（业务级精确四维 key）里历史 P95/P99 阈值做比对
  - 首次跨越 P95：发一次提醒（P95 单次语义，持久化 p95_notified 标志，避免重复打扰；节点重试后重新计）
  - 持续跨越 P99：按指数退避收敛持续推送（复用 `FlowWithNodeDurationReport.should_send` 算法）
  - 消息通道一律复用 `notify.send_msg_for_ai_task_guardian`，不走 AI 调用，纯文本拼装

数据源与依赖：
  - `FlowNode` + `FlowTree.tree`（default 库）：获取运行中节点 + raw_name/component_code
  - `FlowNodeDurationBaseline`（report_db）：读取 P95/P99 等基线指标
  - `FlowWithNodeDurationReport`（default 库）：以 (uid, root_id, node_id) 粒度维护推送收敛记录
  - `NameNormalizer`：把 raw_name 归一化为 normalized_name，作为基线查询第 4 维
  - `FlowTreeParser`：复用 `backend.db_services.flow_node_baseline.sample_collector` 的 tree 展开能力

架构约束：
  - 继承 `SidecarServiceABC`，与 `CheckClusterAlarmForAIService` 对等接入 sidecar 子流程
  - 异常全部内吞 + 日志，`sidecar_func` 恒返回 True，保证不把主 flow 节点拖进 FAILED
  - **仅**业务级基线精确匹配，禁止回退 `bk_biz_id=0` 全局基线
  - `is_reliable=False` 但 P95/P99 > 0 时仍告警，但文案显式携带低置信度免责声明
"""
import logging
import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Iterator, Optional, Tuple

from django.utils import timezone
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator

from backend.core import notify
from backend.db_report.models import FlowNodeDurationBaseline, FlowNodeNameAlias
from backend.db_services.flow_node_baseline.constants import BASELINE_MIN_RELIABLE_SAMPLES, EXCLUDED_COMPONENT_CODES
from backend.db_services.flow_node_baseline.name_cleaner import NameCleaner
from backend.db_services.flow_node_baseline.sample_collector import FlowTreeParser
from backend.flow.consts import StateType
from backend.flow.models import FlowNode, FlowTree, FlowWithNodeDurationReport
from backend.flow.plugins.components.collections.common.sidecar_service_abc import SidecarServiceABC

logger = logging.getLogger("root")


class BreachLevel(Enum):
    """节点耗时相对基线的超线等级。"""

    #: 未超线
    NONE = "none"
    #: 超过 P95 但未超 P99
    P95 = "p95"
    #: 超过 P99
    P99 = "p99"


@dataclass(frozen=True)
class _RunningNode:
    """运行中节点的最小上下文；sidecar 内部使用。"""

    node: FlowNode
    component_code: str
    raw_name: str
    elapsed_seconds: int


class CheckNodeDurationForAIService(SidecarServiceABC):
    """节点耗时超线提醒 sidecar 服务。

    职责：
      - 作为 pipeline 旁路 service 周期性运行；每轮扫描当前 flow 所有运行中节点
      - 把节点"已耗时"与历史基线 P95/P99 比对，命中则发提醒
      - P95 一节点只发一次；P99 走指数退避收敛持续发

    使用方式：
        通过 `CheckNodeDurationForAIComponent` 作为 sidecar act 注入；
        kwargs 支持 `enable_converge`（bool，默认 True）。

    线程安全：否（内部持有 NameNormalizer 的内存缓存；sidecar 单实例单线程调度）
    副作用：读 `FlowNode / FlowTree / FlowNodeDurationBaseline`；读写 `FlowWithNodeDurationReport`；调消息通道
    边界：
      - 任何单节点异常不中断整轮扫描
      - `sidecar_func` 恒返回 True，保证不污染主 flow 节点状态
    """

    interval = StaticIntervalGenerator(30)

    def __init__(self, *args, **kwargs) -> None:
        """构造：仅持有 NameCleaner（分析场景只读查 alias，禁止落库）。

        设计约束：
          - 本服务是基线的"消费者"，不是"生产者"，因此**不**调用 NameNormalizer.normalize()
            （该方法在 cleaned_name 未匹配到任何类别时会写入 FlowNodeNameAlias 并可能触发 LLM）
          - 查不到 alias 的样本一律跳过并打日志，保持 report_db 的写入权只属于 FlowSampleCollector
        """
        super().__init__(*args, **kwargs)
        self._cleaner: NameCleaner = NameCleaner()
        # 本轮扫描的 (tt, code, cleaned_name) → normalized_name 内存缓存
        # 粒度到单轮 _schedule 即可：多节点可能共享同一个 cleaned_name，避免重复 DB 查询
        self._alias_lookup_cache: Dict[Tuple[str, str, str], str] = {}

    # =========================================================================
    # 阶段 1：上下文准备
    # =========================================================================

    def _prepare_context(self, data) -> Optional[Dict]:
        """构造本轮扫描所需的上下文。

        :param data: pipeline data 对象
        :return: dict，字段包含 `root_id / flow_tree / ticket_id / ticket_type / bk_biz_id /
                 enable_converge / now`；失败返回 None
        边界：
          - FlowTree 不存在 → 返回 None（打 error 日志）
          - `flow_tree.uid` 非合法 int → 返回 None（与 CheckClusterAlarmForAIService 行为对齐）
        """
        kwargs = data.get_one_of_inputs("kwargs") or {}
        global_data = data.get_one_of_inputs("global_data") or {}

        enable_converge: bool = bool(kwargs.get("enable_converge", True))
        root_id: str = global_data.get("job_root_id") or ""

        try:
            flow_tree: FlowTree = FlowTree.objects.get(root_id=root_id)
        except FlowTree.DoesNotExist:
            self.log_error(_("[NodeDuration] 查询 FlowTree 失败，root_id={} 不存在").format(root_id))
            return None

        try:
            ticket_id: int = int(flow_tree.uid)
        except (TypeError, ValueError):
            self.log_error(_("[NodeDuration] 查询到 flow 对应的单据ID不合法，uid={}").format(flow_tree.uid))
            return None

        now_time: datetime = timezone.now()
        self.log_info(
            _("[NodeDuration] 本轮扫描 root_id={} ticket_id={} 收敛开关={}").format(
                root_id, ticket_id, _("启用") if enable_converge else _("关闭")
            )
        )

        return {
            "root_id": root_id,
            "flow_tree": flow_tree,
            "ticket_id": ticket_id,
            "ticket_type": flow_tree.ticket_type or "",
            "bk_biz_id": int(flow_tree.bk_biz_id or 0),
            "enable_converge": enable_converge,
            "now": now_time,
        }

    # =========================================================================
    # 阶段 2：运行中节点发现 + 已耗时计算
    # =========================================================================

    def _iter_running_nodes(self, ctx: Dict) -> Iterator[_RunningNode]:
        """以生成器方式产出当前 flow 内所有合法的"运行中节点"。

        流程：
          1. 查 FlowNode: 先对本 root_id 下所有节点做 status 分布统计（排障用，info 日志）
          2. 再过滤出 `status=RUNNING AND started_at IS NOT NULL`
          3. 用 `FlowTreeParser.extract` 展开 tree 得 `{node_id: (component_code, raw_name)}`
          4. 对每个节点做四道过滤：node_id 不在解析结果 / component_code 为空 /
             component_code 命中 `EXCLUDED_COMPONENT_CODES` 黑名单 / 时钟回拨
          5. 计算 `elapsed_seconds = ceil((now - started_at).total_seconds())`

        :param ctx: `_prepare_context` 产出的上下文
        :yield: `_RunningNode`
        边界：
          - tree 解析为空 → 直接返回（打 info 日志）
          - 单节点 label 缺失 / started_at 未来 → 跳过并打 info 日志
          - FlowNode 查询异常 → 打 warning 日志、本轮产出空流
        """
        root_id: str = ctx["root_id"]
        flow_tree: FlowTree = ctx["flow_tree"]
        now_time: datetime = ctx["now"]

        label_map: Dict[str, Tuple[str, str]] = FlowTreeParser.extract(flow_tree.tree)
        if not label_map:
            self.log_info(_("[NodeDuration] tree 解析为空，root_id={}".format(root_id)))
            return

        # 排障诊断：先把 root_id 下**所有节点**的 status 分布打印出来，
        # 便于定位"主流程节点为什么扫不到"——是没 RUNNING？在 SUSPENDED？还是 label_map 对不上？
        try:
            from django.db.models import Count

            status_rows = (
                FlowNode.objects.filter(root_id=root_id)
                .values("status")
                .annotate(cnt=Count("node_id"))
                .order_by("status")
            )
            status_dist: Dict[str, int] = {row["status"]: row["cnt"] for row in status_rows}
            self.log_info(_("[NodeDuration][诊断] root_id={} 当前 FlowNode 状态分布={}".format(root_id, status_dist)))
        except Exception as err:
            self.log_warning(_("[NodeDuration][诊断] 统计 FlowNode 状态分布失败 err={}".format(err)))

        try:
            qs = FlowNode.objects.filter(
                root_id=root_id,
                status=StateType.RUNNING.value,
                started_at__isnull=False,
            ).only("node_id", "started_at", "version_id", "status")
            running_nodes = list(qs)
        except Exception as err:
            self.log_warning(_("[NodeDuration] 查询 FlowNode 失败 root_id={} err={}".format(root_id, err)))
            return

        for node in running_nodes:
            label = label_map.get(node.node_id)
            if label is None:
                # 典型漏召场景一：FlowNode 表里记录了节点，但 tree 解析不含该 node_id
                # 原因可能：SubProcess 父节点 / tree 结构里被当作网关跳过 / 动态插入节点
                self.log_info(
                    _(
                        "[NodeDuration][诊断] node_id={} status={} started_at={} 不在 tree label_map 中，跳过".format(
                            node.node_id, node.status, node.started_at
                        )
                    )
                )
                continue
            component_code, raw_name = label
            if not component_code:
                self.log_info(
                    _("[NodeDuration][诊断] node_id={} raw_name={} component_code 为空，跳过".format(node.node_id, raw_name))
                )
                continue
            if component_code in EXCLUDED_COMPONENT_CODES:
                # 黑名单节点（如 pause / 本服务自身 / check_cluster_alarm_for_ai 等）
                # 与 FlowSampleCollector 对齐：命中黑名单静默跳过，避免高频节点刷屏
                continue

            delta_seconds: float = (now_time - node.started_at).total_seconds()
            if delta_seconds < 0:
                # 时钟回拨：started_at 在未来，不参与告警判定
                self.log_info(
                    _(
                        "[NodeDuration][诊断] node_id={} 时钟回拨（started_at={} now={}），跳过".format(
                            node.node_id, node.started_at, now_time
                        )
                    )
                )
                continue
            elapsed_seconds: int = int(math.ceil(delta_seconds))

            # 候选节点明细：每个通过全部过滤的 running node 都在此落日志，
            # 便于确认"哪些真正进入了后续基线查询"
            self.log_info(
                _(
                    "[NodeDuration][候选] node_id={} code={} raw={} elapsed={}s".format(
                        node.node_id, component_code, raw_name, elapsed_seconds
                    )
                )
            )

            yield _RunningNode(
                node=node,
                component_code=component_code,
                raw_name=raw_name or "",
                elapsed_seconds=elapsed_seconds,
            )

    # =========================================================================
    # 阶段 3：基线查询 + 超线分类
    # =========================================================================

    def _lookup_alias_readonly(
        self,
        ticket_type: str,
        component_code: str,
        raw_name: str,
    ) -> Optional[str]:
        """只读查 alias 表获取 normalized_name；查不到即返回 None，**绝不落库**。

        与 `NameNormalizer.normalize()` 的差异：
          - normalize() 在 cleaned_name 首次出现 / LLM 决策完成 / LLM 调用失败降级
            三种情况下都会调用 `_persist_alias` 把结果写入 `FlowNodeNameAlias`
          - 本方法只走"清洗 → 查 alias 表"两级；查不到就返回 None，由调用方跳过
          - 保证分析场景（本 sidecar）不污染 `report_db` 的基线词典，alias 表的写入
            权只属于采集场景（FlowSampleCollector）

        :param ticket_type: 单据类型
        :param component_code: 组件代码
        :param raw_name: 节点原文名
        :return: 命中返回 normalized_name；清洗后为空或 alias 表未命中返回 None
        边界：
          - cleaned_name 为空 → 返回 None
          - DB 查询异常 → 打 warning 日志、返回 None
          - 复用轮内 `_alias_lookup_cache` 避免对同一 cleaned_name 重复查 DB
        """
        try:
            cleaned_name: str = self._cleaner.clean(raw_name)
        except Exception as err:
            self.log_warning(
                _(
                    "[NodeDuration] NameCleaner 异常 tt={} code={} raw={} err={}".format(
                        ticket_type, component_code, raw_name, err
                    )
                )
            )
            return None
        if not cleaned_name:
            return None

        cache_key: Tuple[str, str, str] = (ticket_type, component_code, cleaned_name)
        hit: Optional[str] = self._alias_lookup_cache.get(cache_key)
        if hit is not None:
            return hit

        try:
            row: Optional[FlowNodeNameAlias] = (
                FlowNodeNameAlias.objects.filter(
                    ticket_type=ticket_type,
                    component_code=component_code,
                    cleaned_name=cleaned_name,
                )
                .only("normalized_name")
                .first()
            )
        except Exception as err:
            self.log_warning(
                _(
                    "[NodeDuration] 查 FlowNodeNameAlias 失败 tt={} code={} cleaned={} err={}".format(
                        ticket_type, component_code, cleaned_name, err
                    )
                )
            )
            return None

        if row is None:
            return None
        self._alias_lookup_cache[cache_key] = row.normalized_name
        return row.normalized_name

    def _lookup_baseline(
        self,
        ticket_type: str,
        bk_biz_id: int,
        component_code: str,
        normalized_name: str,
    ) -> Optional[FlowNodeDurationBaseline]:
        """仅按业务级精确四维 key 查询基线。

        :param ticket_type: 单据类型
        :param bk_biz_id: 业务ID；禁止传 0 做全局兜底
        :param component_code: 组件代码
        :param normalized_name: 归一化节点名
        :return: 命中的基线对象；未命中或阈值无效返回 None
        边界：
          - 未命中返回 None，不回退 `bk_biz_id=0`
          - `p95_seconds <= 0` 或 `p99_seconds <= 0` 视为阈值无效，返回 None
          - DB 查询异常 → 打 warning 日志、返回 None
        """
        try:
            row: Optional[FlowNodeDurationBaseline] = (
                FlowNodeDurationBaseline.objects.filter(
                    ticket_type=ticket_type,
                    bk_biz_id=bk_biz_id,
                    component_code=component_code,
                    normalized_name=normalized_name,
                )
                .only(
                    "sample_count",
                    "is_reliable",
                    "p95_seconds",
                    "p99_seconds",
                    "distribution_type",
                    "mean_seconds",
                    "stddev_seconds",
                    "baseline_version",
                )
                .first()
            )
        except Exception as err:
            self.log_warning(
                _(
                    "[NodeDuration] 查询基线失败 tt={} biz={} code={} name={} err={}".format(
                        ticket_type, bk_biz_id, component_code, normalized_name, err
                    )
                )
            )
            return None

        if row is None:
            return None
        if (row.p95_seconds or 0) <= 0 or (row.p99_seconds or 0) <= 0:
            self.log_info(
                _(
                    "[NodeDuration] 基线阈值无效 tt={} biz={} code={} name={} p95={} p99={}".format(
                        ticket_type,
                        bk_biz_id,
                        component_code,
                        normalized_name,
                        row.p95_seconds,
                        row.p99_seconds,
                    )
                )
            )
            return None

        # 命中：打印基线详情，便于人工核对"查到的基线是否对得上节点语义"
        self.log_info(
            _(
                "[NodeDuration][命中] 基线查询成功 \n"
                "tt={} \n biz={} \n code={} \n name={} \n "
                "p95={}s \n p99={}s \n  "
                "sample_count={} ".format(
                    ticket_type,
                    bk_biz_id,
                    component_code,
                    normalized_name,
                    row.p95_seconds,
                    row.p99_seconds,
                    int(row.sample_count or 0),
                )
            )
        )
        return row

    def _classify_breach(self, elapsed: int, baseline: FlowNodeDurationBaseline) -> BreachLevel:
        """按阈值严格分类超线等级。

        规则：
          - `elapsed > p99` → `P99`
          - `elapsed > p95` → `P95`
          - 其它 → `NONE`

        :param elapsed: 节点已耗时（秒）
        :param baseline: 已命中且阈值有效的基线
        :return: `BreachLevel`
        """
        if elapsed > (baseline.p99_seconds or 0):
            self.log_warning(
                _("[NodeDuration][超线] elapsed={} baseline.p99_seconds={}".format(elapsed, baseline.p99_seconds))
            )
            return BreachLevel.P99
        if elapsed > (baseline.p95_seconds or 0):
            self.log_warning(
                _("[NodeDuration][超线] elapsed={} baseline.p95_seconds={}".format(elapsed, baseline.p95_seconds))
            )
            return BreachLevel.P95
        self.log_info(_("[NodeDuration][正常]耗时分析正常"))
        return BreachLevel.NONE

    # =========================================================================
    # 阶段 4：文案构造
    # =========================================================================

    @staticmethod
    def _build_message(
        level: BreachLevel,
        elapsed_seconds: int,
        baseline: FlowNodeDurationBaseline,
        raw_name: str,
    ) -> str:
        """组装纯文本提醒文案（不走 AI）。

        :param level: 超线等级（P95 / P99）
        :param elapsed_seconds: 已耗时（秒）
        :param baseline: 命中的基线
        :param raw_name: 节点原文名（便于肉眼识别）
        :return: 纯文本文案
        边界：`baseline.is_reliable=False` 时在文案开头加免责声明
        """
        pct_tag: str = "99%" if level == BreachLevel.P99 else "95%"
        header: str = _("⏱️ 节点耗时异常偏高（超过历史 **{pct}** 的同类任务），任务可能存在卡顿，请关注").format(pct=pct_tag)

        lines = [
            header,
            "",
            _("· 节点原名：**{}**").format(raw_name),
            _('· 节点已耗时：<font color="warning">**{} 秒**</font>').format(elapsed_seconds),
            _("· 历史 P95 阈值：**{} 秒**（95% 的同类任务在此时间内完成）").format(int(baseline.p95_seconds or 0)),
            _("· 历史 P99 阈值：**{} 秒**（99% 的同类任务在此时间内完成）").format(int(baseline.p99_seconds or 0)),
        ]

        if not baseline.is_reliable:
            # 低置信度免责声明：告知用户当前基线样本不足，告警仅供参考
            disclaimer: str = _("⚠️ 该基线当前样本量仅 {sample_count} 条,置信度不足（小于基线可靠所需的最小样本数：{samples}），可能存在误报").format(
                sample_count=int(baseline.sample_count or 0), samples=BASELINE_MIN_RELIABLE_SAMPLES
            )
            lines.append(disclaimer)

        # 末尾追加空行：render_title_content 会无条件截掉 content 最后一行，
        # 用空行做牺牲行，避免有效内容（P99 阈值行 / disclaimer）被裁剪
        lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # 阶段 5：P95 / P99 推送分支
    # =========================================================================

    def _get_report(
        self,
        ctx: Dict,
        rn: _RunningNode,
        normalized_name: str,
    ) -> Optional[FlowWithNodeDurationReport]:
        """获取节点推送收敛记录；若检测到节点重试则先重置推送状态。

        :param ctx: 上下文
        :param rn: 运行中节点
        :param normalized_name: 归一化名
        :return: 收敛记录；DB 异常返回 None
        """
        try:
            report, created = FlowWithNodeDurationReport.objects.get_or_create(
                uid=str(ctx["ticket_id"]),
                root_id=ctx["root_id"],
                node_id=rn.node.node_id,
                defaults={
                    "component_code": rn.component_code,
                    "normalized_name": normalized_name,
                    "enable_converge": ctx["enable_converge"],
                },
            )
        except Exception as err:
            self.log_warning(_("[NodeDuration] get_or_create 失败 node_id={} err={}".format(rn.node.node_id, err)))
            return None

        if not created:
            self._reset_if_new_execution(report, rn)
        return report

    def _reset_if_new_execution(self, report: FlowWithNodeDurationReport, rn: _RunningNode) -> None:
        """节点重试识别：上次推送时间早于本次 started_at，说明记录属于旧执行，整体重置。

        背景：节点重试时 node_id 不变，但 post_set_state 信号会把 FlowNode.started_at 刷新为新时间；
        而同一次执行内推送必然发生在超线之后（last_send_time 恒晚于 started_at），因此不会误判。
        重置 p95_notified / send_count / last_send_time / last_risk_level 等，
        保证重试后的新一次执行能重新收到 P95 提醒、P99 退避窗口从初始值重新起算。

        :param report: 收敛记录
        :param rn: 运行中节点
        边界：
          - last_send_time 为空（从未成功推送过）→ 无需重置
          - DB 异常 → 打日志、不上抛
        """
        last_send_time: Optional[datetime] = report.last_send_time
        if last_send_time is None or last_send_time >= rn.node.started_at:
            return

        self.log_info(
            _(
                "[NodeDuration] 检测到节点重试 node_id={} last_send_time={} started_at={}，重置推送状态".format(
                    rn.node.node_id, last_send_time, rn.node.started_at
                )
            )
        )
        try:
            report.p95_notified = False
            report.send_count = 0
            report.last_send_time = None
            report.last_risk_level = ""
            report.last_report_content = ""
            report.no_risk_streak = 0
            report.save(
                update_fields=[
                    "p95_notified",
                    "send_count",
                    "last_send_time",
                    "last_risk_level",
                    "last_report_content",
                    "no_risk_streak",
                ]
            )
        except Exception as err:
            self.log_warning(_("[NodeDuration] 重置推送状态失败 node_id={} err={}".format(rn.node.node_id, err)))

    def _handle_p95(
        self,
        ctx: Dict,
        rn: _RunningNode,
        baseline: FlowNodeDurationBaseline,
        normalized_name: str,
    ) -> None:
        """P95 单次提醒分支：持久化 p95_notified 标志保证只发一次。

        :param ctx: 上下文
        :param rn: 运行中节点
        :param baseline: 已命中基线
        :param normalized_name: 归一化名
        边界：
          - 节点重试后（FlowNode.started_at 刷新）由 `_reset_if_new_execution` 重置 p95_notified，
            新一次执行可重新收到 P95 提醒
          - DB / 推送异常 → 打日志、不上抛
          - 推送失败 → 不更新 p95_notified，下一轮重试
          - 推送成功同时写入 last_send_time（用于节点重试识别）；send_count 不变，
            不影响 P99 的首次推送判定
        """
        report = self._get_report(ctx, rn, normalized_name)
        if report is None:
            return

        if report.p95_notified:
            self.log_info(_("[NodeDuration] P95 已发过，跳过 node_id={}".format(rn.node.node_id)))
            return

        content: str = self._build_message(
            level=BreachLevel.P95,
            elapsed_seconds=rn.elapsed_seconds,
            baseline=baseline,
            raw_name=rn.raw_name,
        )

        try:
            self.log_info(
                _("[NodeDuration] 推送 P95 提醒 node_id={} elapsed={}s".format(rn.node.node_id, rn.elapsed_seconds))
            )
            notify.send_msg_for_ai_task_guardian(ticket_id=ctx["ticket_id"], ai_result=content)
        except Exception as err:
            # 推送失败不更新 p95_notified，下一轮重试
            self.log_error(_("[NodeDuration] P95 推送失败 node_id={} err={}".format(rn.node.node_id, err)))
            return

        try:
            report.p95_notified = True
            report.last_send_time = timezone.now()
            # 顺带回填审计字段（可能首次 get_or_create 后属性为空）
            if not report.component_code:
                report.component_code = rn.component_code
            if not report.normalized_name:
                report.normalized_name = normalized_name
            report.save(update_fields=["p95_notified", "last_send_time", "component_code", "normalized_name"])
        except Exception as err:
            self.log_warning(_("[NodeDuration] P95 更新标志失败 node_id={} err={}".format(rn.node.node_id, err)))

    def _handle_p99(
        self,
        ctx: Dict,
        rn: _RunningNode,
        baseline: FlowNodeDurationBaseline,
        normalized_name: str,
    ) -> None:
        """P99 收敛提醒分支：复用指数退避收敛算法。

        :param ctx: 上下文
        :param rn: 运行中节点
        :param baseline: 已命中基线
        :param normalized_name: 归一化名
        边界：
          - 节点重试后由 `_reset_if_new_execution` 重置 send_count 等退避状态，
            新一次执行的第一条 P99 提醒立即推送
          - `enable_converge=False` 时走 `should_send` 的"收敛未启用"分支，每次都发
          - DB / 推送异常 → 打日志、不上抛
        """
        report = self._get_report(ctx, rn, normalized_name)
        if report is None:
            return

        # 若 kwargs 开关变化，刷到最新；避免老记录卡在旧状态
        if report.enable_converge != ctx["enable_converge"]:
            report.enable_converge = ctx["enable_converge"]
            try:
                report.save(update_fields=["enable_converge"])
            except Exception as err:
                self.log_warning(
                    _("[NodeDuration] P99 更新 enable_converge 失败 node_id={} err={}".format(rn.node.node_id, err))
                )

        try:
            should_send, reason = report.should_send(current_risk_level="high", is_same_risk=None)
        except Exception as err:
            self.log_warning(
                _("[NodeDuration] P99 should_send 异常，降级为允许推送 node_id={} err={}".format(rn.node.node_id, err))
            )
            should_send, reason = True, _("should_send 异常降级")

        self.log_info(
            _("[NodeDuration] P99 收敛判定 node_id={} 允许推送={} 原因={}".format(rn.node.node_id, should_send, reason))
        )
        if not should_send:
            return

        content: str = self._build_message(
            level=BreachLevel.P99,
            elapsed_seconds=rn.elapsed_seconds,
            baseline=baseline,
            raw_name=rn.raw_name,
        )

        try:
            self.log_info(
                _("[NodeDuration] 推送 P99 提醒 node_id={} elapsed={}s".format(rn.node.node_id, rn.elapsed_seconds))
            )
            notify.send_msg_for_ai_task_guardian(ticket_id=ctx["ticket_id"], ai_result=content)
        except Exception as err:
            self.log_error(_("[NodeDuration] P99 推送失败 node_id={} err={}".format(rn.node.node_id, err)))
            return

        try:
            report.record_send(risk_level="high", report_content=content)
            # 顺带回填审计字段
            dirty = []
            if not report.component_code:
                report.component_code = rn.component_code
                dirty.append("component_code")
            if not report.normalized_name:
                report.normalized_name = normalized_name
                dirty.append("normalized_name")
            if dirty:
                report.save(update_fields=dirty)
        except Exception as err:
            self.log_warning(_("[NodeDuration] P99 record_send 失败 node_id={} err={}".format(rn.node.node_id, err)))

    # =========================================================================
    # 阶段 6：主入口
    # =========================================================================

    def sidecar_func(self, data, parent_data) -> bool:
        """旁路服务主入口：发现 → 归一化 → 查基线 → 分类 → 推送。

        :param data: pipeline data
        :param parent_data: pipeline parent data
        :return: 恒 True（保证不污染主 flow 节点状态）
        边界：全程异常内吞 + 日志；单节点失败不中断整轮
        """
        self.log_info("=================================")
        ctx: Optional[Dict] = self._prepare_context(data)
        if ctx is None:
            return True

        processed: int = 0
        for rn in self._iter_running_nodes(ctx):
            try:
                # 归一化（只读查 alias，不落库、不调 LLM）
                normalized_name: Optional[str] = self._lookup_alias_readonly(
                    ticket_type=ctx["ticket_type"],
                    component_code=rn.component_code,
                    raw_name=rn.raw_name,
                )
                if not normalized_name:
                    # 未命中 alias 表：可能是全新变体（基线也无从比对），
                    # 也可能是"已有同桶但本 cleaned_name 本次首见"（存在召回缺口，
                    # 需后续基于日志数据观测再决定是否引入兜底策略）
                    self.log_info(
                        _(
                            "[NodeDuration] alias 未命中，证明这个节点之前没有统计耗时情况 "
                            "tt={} code={} raw={} node_id={}；本轮跳过".format(
                                ctx["ticket_type"], rn.component_code, rn.raw_name, rn.node.node_id
                            )
                        )
                    )
                    continue

                # 基线查询（仅业务级精确匹配）
                baseline = self._lookup_baseline(
                    ticket_type=ctx["ticket_type"],
                    bk_biz_id=ctx["bk_biz_id"],
                    component_code=rn.component_code,
                    normalized_name=normalized_name,
                )
                if baseline is None:
                    self.log_info(
                        _(
                            "[NodeDuration] 没有命中到对应耗时基线统计 "
                            "tt={} biz={} code={} name={} node_id={}".format(
                                ctx["ticket_type"],
                                ctx["bk_biz_id"],
                                rn.component_code,
                                normalized_name,
                                rn.node.node_id,
                            )
                        )
                    )
                    continue

                # 超线分类 + 分支
                level: BreachLevel = self._classify_breach(rn.elapsed_seconds, baseline)
                if level == BreachLevel.NONE:
                    continue
                if level == BreachLevel.P99:
                    # 跨越 P99 时只走 P99 分支，不叠加 P95
                    self._handle_p99(ctx, rn, baseline, normalized_name)
                else:
                    self._handle_p95(ctx, rn, baseline, normalized_name)

                processed += 1
            except Exception as err:
                # 单节点异常不中断整轮
                self.log_warning(
                    _("[NodeDuration] 处理单节点异常 node_id={} err={}".format(getattr(rn.node, "node_id", "?"), err))
                )

        if processed == 0:
            self.log_info(_("[NodeDuration] 本轮未产生任何告警 root_id={}".format(ctx["root_id"])))

        return True


class CheckNodeDurationForAIComponent(Component):
    """节点耗时超线提醒 Component（sidecar 子流程接入点）。

    Attributes:
        name:          Component 名称（使用模块名，与仓内其它 sidecar 一致）
        code:          Component 唯一标识；同步出现在 `EXCLUDED_COMPONENT_CODES` 黑名单中
        bound_service: 绑定的 Service 类
    """

    name = __name__
    code = "sidecar_check_node_duration_for_ai"
    bound_service = CheckNodeDurationForAIService
