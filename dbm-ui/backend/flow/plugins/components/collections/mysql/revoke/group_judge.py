# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主机退回资源池 · 组级判定 bamboo Service / Component。

模块职责：
  - :class:`ResourceGroupJudgeService` 承担"组级判定汇聚"任务：
      1) 读取上游 :class:`MySQLHostProcessCheckComponent` 写入 ``trans_data.host_process_check``
         的每台机器 <ctx> JSON（结构 ``{ip: <ctx_dict>}``）
      2) 对组内每台机器构造 :class:`HostRevokeChecker` 分别跑 F1/F2/F3/F4 判据
      3) 调 :class:`HostDecisionMatrix` 得单机 :class:`RevokeVerdict`
      4) 调 :class:`ResourceGroupChecker` 跑 G1 组级判据
      5) 调 :class:`GroupDecisionMatrix` 得 :class:`GroupVerdict`
      6) 将 GroupVerdict 序列化为 dict 写入 ``trans_data.group_verdict``，
         组决策字符串写入 ``trans_data.group_verdict_decision``，供下游清理子流程读取
  - **只判定不清理**：本节点绝不修改任何元数据、不发起变更类 RPC

判据代号 · 业务翻译（首次并列翻译清单，后续直接用代号）：
  - **F1 · 所有权**：本机最近一次 MachineEvent 的 ticket_id 是否等于本单据（不是则视作与本单无关）
  - **F2 · 客户端流量红线**：本机是否仍被客户端引用（DNS 域名 / CLB 后端 / proxy 的 backends 三处任一命中即红线）
  - **F3 · DBM 元数据残留**：DBM 侧 Machine / ProxyInstance / StorageInstance / StorageInstanceTuple 四张表是否还有本机记录
  - **F4 · 进程存活**：本机上是否还在跑 MySQL / mysql-proxy / mariadbd 等 MySQL 家族进程
  - **G1 · 组内一致性**：组内所有机器的单机决策是否完全一致（不一致则挂起等 DBA 排查）

组决策取值 · 业务翻译：
  - **GROUP_RECYCLE**：本组可安全自动清理（下游走完整清理链路 A/C/D/E）
  - **GROUP_MANUAL**：本组挂起等人工处置（下游 no-op；同时产出 WARNING 结构化日志供告警平台捕获）
  - **GROUP_SKIP**：本组不属于本单据（下游 no-op）
  - **GROUP_KEEP**：本组仍在服务，红线保留（下游 no-op）

下游耦合：下游 :class:`ResourceGroupCleanupService` 依据 ``trans_data.group_verdict_decision`` 分支决定
  是否清理、是否 no-op；本 Service 是清理链路的"唯一决策入口"。

设计要点：
  - 组级判定天然是"汇聚型"活动，不适合再拆分为并行节点；每组一个 Service 实例
  - 组内单机判据本身独立，但为了简化编排，本 Service 在同一节点内串行跑 F1/F2/F3/F4，
    避免多节点间为传递 F 判据结果引入额外的 trans_data 字段
  - 输出统一用 dataclasses.asdict 序列化为纯 dict，避免 bamboo 跨节点序列化 dataclass 问题
  - **静态字段名**：与 :class:`RevokeTransData` 预声明字段一一对应；SubProcess 隔离保证组间无冲突

模块边界：
  - kwargs 关键字段缺失 -> log error 返回 False，节点失败（避免下游拿到空 verdict 误判）
  - 单机 F 判据全部收敛为 UNKNOWN 不上抛
  - 单个机器判据失败不影响其他机器判定
  - 判据采集实现细节在 :mod:`backend.flow.engine.revoke.host_check` / :mod:`.group_check`；
    决策矩阵纯函数在 :mod:`.decision`；本模块只做"编排 + 汇聚 + 出参写入"
"""
import json
import logging
from dataclasses import asdict
from enum import Enum
from typing import Any, Dict, List, Tuple

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.flow.engine.bamboo.scene.common.machine_os_init import RecycleOutputContext
from backend.flow.engine.bamboo.scene.mysql.revoke.base.decision import GroupDecisionMatrix, HostDecisionMatrix
from backend.flow.engine.bamboo.scene.mysql.revoke.base.group_check import (
    ResourceGroupChecker,
    build_group_warning_log,
)
from backend.flow.engine.bamboo.scene.mysql.revoke.base.host_check import HostRevokeChecker
from backend.flow.engine.bamboo.scene.mysql.revoke.base.log_utils import (
    extract_decision_reason,
    f1_zh,
    f2_title_by_role,
    f2_zh,
    f3_zh,
    f4_zh,
    g1_zh,
    group_decision_zh,
    host_decision_zh,
)
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import (
    F2_SUB_KEY_DNS,
    FactCheckOutcome,
    FactState,
    GroupDecision,
    GroupVerdict,
    HostRevokeFacts,
    ResourceGroup,
    RevokeUnit,
    RevokeVerdict,
)
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import FlowOutputHandler
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


class ResourceGroupJudgeService(BaseService):
    """组级判定汇聚 bamboo Service。

    职责：把一组资源组的 F1~F4 单机判据 + G1/G2 组级判据 汇聚成一个 GROUP_* 组决策，
    并把决策结果写回 trans_data 供下游清理子流程使用。**只判定、不清理**。

    kwargs 契约（上层建节点时必须传入）：
      - ``group_dict``       (dict, 必填)  由 ``dataclasses.asdict(group)`` 序列化的 ResourceGroup
        （已含 ``clb_regions`` 字段：F2.b CLB 需检查的 region 列表；Extractor 装配时写入）
      - ``ticket_id``        (int, 必填)  当前 revoke 所属的原单据 id

    trans_data 输入（由段 1 :class:`MySQLHostProcessCheckService` APPEND 模式写入）：
      - ``host_process_check``   ``{ip: <ctx_dict>}``  每台机器的进程扫描 <ctx> JSON

    trans_data 输出（供段 3 :class:`ResourceGroupCleanupService` 消费）：
      - ``group_verdict``            asdict 序列化的 :class:`GroupVerdict` dict
      - ``group_verdict_decision``   :class:`GroupDecision` 的 .value 字符串
        （便于清理子流程分支判断，避免嵌套 dict 取值）

    外部落地（本节点在 GROUP_RECYCLE 判决产出瞬间同步执行）：
      - 通过 :class:`FlowOutputHandler(RecycleOutputContext.ToResourceSerializer)` 把本组
        **所有 units**（按 ``gv.verdicts`` 全量）预申报写入 FlowSummary；GROUP_RECYCLE 契约
        保证组内所有机器均需退回资源池，因此不做任何子状态过滤。
      - **语义变更**：FlowSummary 记录的含义由"已完成元数据清理的机器"更新为
        "决策判定需要退回资源池的机器"（预申报语义）。段 3 清理失败挂起时，
        FlowSummary 记录保持不变，由 DBA 原地重试段 3（``_cleanup_one_host`` 幂等）。
      - 该写入**不改变判决、不阻塞节点**：insert_data 异常仅记 ERROR 日志，继续走后续流程。

    判定决策逻辑：
      **F1~F4 单机判据**（含义详见模块级 docstring 首部翻译清单）：
        F1=所有权 · F2=客户端流量红线 · F3=DBM 元数据残留 · F4=进程存活
      **单机决策**（``HostDecisionMatrix.classify``；4 个决策业务含义）：
        SKIP=与本单无关跳过 · KEEP=有流量必须保留 · MANUAL=不确定挂起 · RECYCLE=可安全清理
      **单机决策关键分支**：
        - F1=NO/UNKNOWN → SKIP（机器不属于本单据，短路）
        - F1=YES + F2=YES + F3=YES + F4=YES → KEEP（红线正在服务）
        - F1=YES + F2=YES 但 F3/F4 有一项 NO/UNKNOWN → MANUAL（有流量但数据一致性异常）
        - F1=YES + F2=UNKNOWN → MANUAL（红线判据不确定，保守挂起）
        - F1=YES + F2=NO + F4=YES/NO → RECYCLE（无流量、进程状态已知，可清理）
        - F1=YES + F2=NO + F4=UNKNOWN → MANUAL（进程未知不敢自动清理）
      **G1 组级判据**：G1=组内一致性
      **组决策关键分支**（``GroupDecisionMatrix.classify``）：
        - G1=NO/UNKNOWN → GROUP_MANUAL（组内单机结论不一致，挂起）
        - G1=YES + 全 SKIP → GROUP_SKIP · 全 KEEP → GROUP_KEEP · 全 RECYCLE → GROUP_RECYCLE
        - G1=YES 但组内结论构成异常（含 MANUAL / RECYCLE+KEEP 等）→ GROUP_MANUAL

    线程安全：非线程安全（Service 生命周期由 bamboo 管理，单节点单实例）
    边界：
      - kwargs 关键字段缺失 -> log error 返回 False
      - group_dict 反序列化失败 -> log error 返回 False
      - trans_data.host_process_check 缺失 / 非 dict -> log error 返回 False
      - 内部判据异常均收敛为 FactState.UNKNOWN，不上抛
    """

    def _execute(self, data, parent_data) -> bool:
        """执行组级判定汇聚（编排骨架）。

        本方法仅承担\"编排\"职责，按顺序调用 7 个私有方法，不含任何业务分支：
          1. :meth:`_parse_kwargs`            参数校验 + group / ticket 反序列化
          2. :meth:`_load_ctx_dict`           读取上游进程扫描 <ctx> dict
          3. :meth:`_classify_hosts`          逐台机器跑 F1/F2/F3/F4 并产出单机结论
          4+5. :meth:`_classify_group`        G1 组一致性 + 组决策 + 组级日志 + MANUAL warning
          6. :meth:`_write_trans_data`        把 GroupVerdict 写回 trans_data
          6.5. :meth:`_pre_declare_flow_summary` GROUP_RECYCLE 时写 FlowSummary 预申报
          7. :meth:`_emit_manual_failure_log` GROUP_MANUAL 时输出失败引导日志并 return False

        :param data: bamboo 节点数据对象
        :param parent_data: bamboo 父节点数据对象（不使用）
        :return: True 判定完成；False 表示节点失败（关键字段缺失 / GROUP_MANUAL 主动挂起）
        边界：
          - 任一关键字段缺失 / 反序列化失败 -> 对应子方法 log error 后 return False，节点失败
          - 单机 F 判据 / 组级 G1 判据的所有异常均在下层收敛为 FactState.UNKNOWN，不上抛到本方法
        """
        kwargs: Dict[str, Any] = data.get_one_of_inputs("kwargs") or {}
        node_name: str = kwargs.get("node_name") or self.__class__.__name__

        # ---- 1. 参数校验与反序列化 ----
        parsed = self._parse_kwargs(kwargs, node_name)
        if parsed is None:
            return False
        group, ticket, root_id = parsed
        self.log_info(_("开始判定本组 {n} 台主机（单据 {ticket_id}）").format(n=len(group.units), ticket_id=ticket.id))

        # ---- 2. 读取上游进程检查节点写入的组级 <ctx> dict ----
        trans_data = data.get_one_of_inputs("trans_data")
        ctx_by_ip = self._load_ctx_dict(trans_data, group, node_name)
        if ctx_by_ip is None:
            return False

        # ---- 3. 对每台机器串行跑 F1/F2/F3/F4，产出 RevokeVerdict ----
        verdicts_tuple = self._classify_hosts(group=group, ticket=ticket, root_id=root_id, ctx_by_ip=ctx_by_ip)

        # ---- 4+5. 组级 G1 判据 + 组决策 + 组级日志 + MANUAL warning ----
        gv = self._classify_group(group=group, verdicts=verdicts_tuple, root_id=root_id)

        # ---- 6. 将 GroupVerdict 写入 trans_data ----
        if not self._write_trans_data(data=data, trans_data=trans_data, gv=gv, node_name=node_name):
            return False

        # ---- 6.5 FlowSummary 预申报写入（仅 GROUP_RECYCLE 触发）----
        if gv.decision == GroupDecision.GROUP_RECYCLE:
            self._pre_declare_flow_summary(data=data, gv=gv, group=group)

        # ---- 7. GROUP_MANUAL 时主动失败，供 DBA 在 pipeline UI 人工确认 ----
        if gv.decision == GroupDecision.GROUP_MANUAL:
            self._emit_manual_failure_log(gv)
            return False

        return True

    # ------------------------------------------------------------------
    # 以下私有方法按 _execute 执行顺序排列，每个方法单一职责，便于单测
    # ------------------------------------------------------------------

    def _parse_kwargs(self, kwargs: Dict[str, Any], node_name: str) -> "Tuple[ResourceGroup, Ticket, str] | None":
        """参数校验 + group_dict / ticket 反序列化。

        :param kwargs: bamboo 节点 kwargs
        :param node_name: 日志前缀用的节点名
        :return: (group, ticket, root_id) 三元组；校验失败返回 None。
        边界：
          - group_dict 非 dict / ticket_id 非 int / 反序列化失败 / Ticket 不存在 -> log error 返回 None
        """
        group_dict = kwargs.get("group_dict")
        ticket_id = kwargs.get("ticket_id")

        if not isinstance(group_dict, dict):
            self.log_error(_("[{}] kwargs.group_dict 缺失或非 dict").format(node_name))
            return None
        if not isinstance(ticket_id, int):
            self.log_error(_("[{}] kwargs.ticket_id 缺失或非 int").format(node_name))
            return None

        try:
            group: ResourceGroup = ResourceGroup.from_dict(group_dict)
        except Exception as err:
            self.log_error(_("[{}] group_dict 反序列化失败: {}").format(node_name, err))
            return None

        try:
            ticket: Ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            self.log_error(_("[{}] 单据 ticket_id={} 不存在").format(node_name, ticket_id))
            return None

        root_id: str = kwargs.get("root_id") or "unknown-root"
        return group, ticket, root_id

    def _load_ctx_dict(self, trans_data: Any, group: ResourceGroup, node_name: str) -> "Dict[str, Any] | None":
        """从 trans_data.host_process_check 中读取每台机器的进程扫描 <ctx>。

        :param trans_data: bamboo trans_data
        :param group: 本组资源组
        :param node_name: 日志前缀用的节点名
        :return: ``{ip: ctx_dict}``；校验失败返回 None
        边界：
          - trans_data.host_process_check 非 dict -> log error 返回 None
          - trans_data is None 时视为 {}（下层 F4 判据会收敛为 UNKNOWN）
        """
        ctx_dict_all: Dict[str, Any] = (
            getattr(trans_data, "host_process_check", None) if trans_data is not None else None
        ) or {}
        if not isinstance(ctx_dict_all, dict):
            self.log_error(
                _("[{}] trans_data.host_process_check 期望为 dict{{ip: ctx}}，实际={}").format(
                    node_name, type(ctx_dict_all).__name__
                )
            )
            return None
        self.log_info(json.dumps(ctx_dict_all))
        return {u.ip: ctx_dict_all.get(u.ip) for u in group.units}

    def _classify_hosts(
        self,
        *,
        group: ResourceGroup,
        ticket: Ticket,
        root_id: str,
        ctx_by_ip: Dict[str, Any],
    ) -> Tuple[RevokeVerdict, ...]:
        """对组内每台机器串行跑 F1/F2/F3/F4，产出 :class:`RevokeVerdict` 元组。

        :param group: 本组资源组
        :param ticket: 单据对象（F1 所有权判据需要）
        :param root_id: pipeline root_id（用于日志）
        :param ctx_by_ip: ``{ip: ctx}`` 来自上游进程扫描
        :return: 单机结论元组，顺序与 group.units 对齐
        边界：
          - 单机 F 判据内部异常均在 HostRevokeChecker 中收敛为 UNKNOWN，本方法不处理异常
        """
        verdicts: List[RevokeVerdict] = []
        for u in group.units:
            checker = HostRevokeChecker(
                root_id=root_id,
                ticket=ticket,
                bk_biz_id=u.bk_biz_id,
                bk_cloud_id=u.bk_cloud_id,
                ip=u.ip,
                bk_host_id=u.bk_host_id,
            )
            f1 = checker.check_f1_ownership(unit=u)
            f2 = checker.check_f2_traffic(
                unit=u,
                clb_regions=list(group.clb_regions),
                access_layer_proxies=group.access_layer_proxies,
                # F2.c / F2.d 接入层存活性预判所需的"本组视图"：
                #   - group_units：供 R3 跨组兜底判断（proxy 的 ip 不在本组则视为活）
                #   - host_process_check_ctx_by_ip：组内 proxy 走 F4 判据口径筛选存活性
                group_units=group.units,
                host_process_check_ctx_by_ip=ctx_by_ip,
            )
            f3 = checker.check_f3_dbm_residue(unit=u)
            f4 = HostRevokeChecker.check_f4_process(ctx_by_ip.get(u.ip), ip=u.ip)
            facts = HostRevokeFacts(f1_ownership=f1, f2_traffic=f2, f3_dbm_residue=f3, f4_process=f4)
            verdict = HostDecisionMatrix.classify(unit=u, facts=facts)
            self._log_host_verdict(unit=u, facts=facts, verdict=verdict)
            verdicts.append(verdict)
        return tuple(verdicts)

    def _log_host_verdict(self, *, unit: RevokeUnit, facts: HostRevokeFacts, verdict: RevokeVerdict) -> None:
        """输出单台机器的 \"检测项 + 判定结果\" 多行日志块。

        :param unit: 单机 RevokeUnit
        :param facts: F1~F4 判据聚合
        :param verdict: 单机决策结果

        日志设计：
          - 检测项每行末尾按 **判据的"异常态"** 条件追加判据级 reason：
              * F1 异常态 = NO（不归属本单才需要 DBA 关注）
              * F2/F3/F4 异常态 = YES（有流量/有残留/有进程才需要 DBA 关注）
              * UNKNOWN 一律打印（无法确认是排查刚需）
            期望态静默以减少噪音，让 DBA 一眼聚焦异常项
          - **F2 标题按 role 路由**（对齐 :meth:`check_f2_traffic` 的 3 条判据路径）：
              * REMOTE_*     → "是否被 tdbctl 中控路由引用"（F2.c 判据）
              * BACKEND_MASTER / BACKEND_REPEATER → "是否被 proxy 作为后端引用"（F2.d 判据）
              * 其他角色（PROXY / SPIDER / ORPHAN / BACKEND_SLAVE / ...） → "是否绑定 DNS 或 CLB 服务"（F2.a + F2.b 判据）
            通过 :func:`f2_title_by_role` 统一路由，避免对 master 等不走 DNS/CLB 的角色
            错误展示 "是否绑定 DNS 或 CLB 服务" 这一误导性标题
          - F2=YES 时额外列出命中的 DNS 域名清单（取 ``F2_SUB_KEY_DNS`` 子字段，
            常量化避免字符串漂移导致漏显示）
        """
        f1, f2, f3, f4 = facts.f1_ownership, facts.f2_traffic, facts.f3_dbm_residue, facts.f4_process

        # ── F2=YES 时从 evidence 中提取 DNS 域名列表（样式 γ），其余状态保持空串避免日志噪音
        # 外层键名使用 models.F2_SUB_KEY_DNS 常量（真实值 "f2a_dns"），内层字段 "domain_names"
        # 由 _sub_check_f2a_dns 产出；避免历史字符串字面量漂移导致该行永远取不到值
        f2_dns_lines: str = ""
        if f2.state == FactState.YES and isinstance(f2.evidence, dict):
            dns_sub: Dict[str, Any] = f2.evidence.get(F2_SUB_KEY_DNS) or {}
            domain_names: List[str] = list(dns_sub.get("domain_names") or [])
            if domain_names:
                f2_dns_lines = "\n" + "\n".join(_("     └─ DNS 域名: {}").format(d) for d in domain_names)

        # ── F1~F4 分级 reason（按判据的"异常态"决定何时追加原因行）：
        # F1 异常态 = NO（不归属本单据），F2/F3/F4 异常态 = YES（有流量/有残留/有进程），
        # UNKNOWN 一律打印；期望态静默
        f1_reason = self._format_reason_line(f1, anomaly_state=FactState.NO)
        f2_reason = self._format_reason_line(f2)
        f3_reason = self._format_reason_line(f3)
        f4_reason = self._format_reason_line(f4)

        # ── F2 检测项标题按 unit.role 动态路由，贴合 check_f2_traffic 的 3 条判据路径
        f2_title: str = f2_title_by_role(unit.role)

        self.log_info(
            _(
                "\n{sep}\n"
                "主机: {ip}\n"
                "主机ID: {host_id}\n"
                "角色: {role}\n"
                "\n"
                "【检测项】\n"
                "  ① 是否归属本单据的主机       : {f1_zh}{f1_reason}\n"
                "  ② {f2_title}: {f2_zh}{f2_reason}{f2_dns_lines}\n"
                "  ③ 是否有元数据残留           : {f3_zh}{f3_reason}\n"
                "  ④ 进程是否存活               : {f4_zh}{f4_reason}\n"
                "\n"
                "【判定结果】\n"
                "  {decision_zh}（{decision}）\n"
                "  说明: {reason}\n"
                "{sep}"
            ).format(
                sep="━" * 60,
                ip=unit.ip,
                host_id=unit.bk_host_id,
                role=unit.role,
                f1_zh=f1_zh(f1.state.value),
                f1_reason=f1_reason,
                f2_title=f2_title,
                f2_zh=f2_zh(f2.state.value),
                f2_reason=f2_reason,
                f2_dns_lines=f2_dns_lines,
                f3_zh=f3_zh(f3.state.value),
                f3_reason=f3_reason,
                f4_zh=f4_zh(f4.state.value),
                f4_reason=f4_reason,
                decision_zh=host_decision_zh(verdict.decision.value),
                decision=verdict.decision.value.upper(),
                reason=extract_decision_reason(verdict.reason),
            )
        )

    @staticmethod
    def _format_reason_line(f: FactCheckOutcome, anomaly_state: FactState = FactState.YES) -> str:
        """按判据的"异常态"分级追加 reason 行（UNKNOWN 永远打印，异常态必打，期望态静默）。

        设计意图：
          - 每条 F 判据都有明确的"异常态"（需要 DBA 关注、介入或排查的状态）与
            "期望态"（revoke 流程希望看到的、无需关注的默认状态）：
              * F1 异常态=NO（不归属本单据），期望态=YES（归属本单，可继续走判定）
              * F2 异常态=YES（有流量红线），期望态=NO（无流量，可清理）
              * F3 异常态=YES（有元数据残留），期望态=NO 或 YES 均可
              * F4 异常态=YES（进程存活），期望态=NO 或 YES 均可
            注意 F1 的"期望态/异常态"方向与 F2/F3/F4 相反（F1 判据内部查的是"归属"
            这一正向命题），因此调用处必须显式传入 ``anomaly_state=FactState.NO``
          - UNKNOWN 永远打印：无论哪条判据，判据无法确认都是 DBA 排查刚需，
            reason 中通常附带 error 根因，价值更高
          - 期望态静默：避免反复输出"XX 未命中 / 正常 / 一致"这类无效噪音，
            让异常机器不被淹没在正常机器里

        :param f: 单条判据结果；``f.reason`` 为空时整体静默
        :param anomaly_state: 本判据的"异常态"；F2/F3/F4 用默认值 ``FactState.YES``，
            F1 显式传 ``FactState.NO``
        :return: 追加到检测项行末的 reason 片段，形如 ``"\\n     └─ 原因: xxx"``；
            期望态 / reason 为空时返回空串
        """
        # UNKNOWN 永远打印；异常态必打；期望态（既非 UNKNOWN 也非 anomaly_state）静默
        if f.state != FactState.UNKNOWN and f.state != anomaly_state:
            return ""
        reason_text: str = (f.reason or "").strip()
        if not reason_text:
            return ""
        return _("\n     └─ 原因: {}").format(reason_text)

    def _classify_group(
        self, *, group: ResourceGroup, verdicts: Tuple[RevokeVerdict, ...], root_id: str
    ) -> GroupVerdict:
        """组级 G1 判据 + 组决策矩阵 + 组日志 + MANUAL warning。

        :param group: 本组资源组
        :param verdicts: 单机决策元组
        :param root_id: pipeline root_id（供 ResourceGroupChecker）
        :return: :class:`GroupVerdict` 组决策结果
        """
        group_checker = ResourceGroupChecker(root_id=root_id)
        g1 = group_checker.check_g1_consistency(verdicts)
        gv: GroupVerdict = GroupDecisionMatrix.classify(group=group, verdicts=verdicts, g1=g1)

        ip_lines: str = "\n".join("    - {}".format(u.ip) for u in group.units)
        self.log_info(
            _(
                "\n{sep}\n"
                "本组判定结论\n"
                "{sep}\n"
                "\n"
                "  组 ID       : {group_id}\n"
                "  组内主机数  : {n} 台\n"
                "\n"
                "  组内主机    :\n"
                "{ip_lines}\n"
                "\n"
                "  【组级检测】\n"
                "    ⑤ 组内单机结论一致性  : {g1_zh}\n"
                "\n"
                "  【最终决策】\n"
                "    {decision_zh}（{decision}）\n"
                "    说明: {reason}\n"
                "{sep}"
            ).format(
                sep="━" * 60,
                group_id=group.group_id,
                n=len(group.units),
                ip_lines=ip_lines,
                g1_zh=g1_zh(g1.state.value),
                decision_zh=group_decision_zh(gv.decision.value),
                decision=gv.decision.value.upper(),
                reason=extract_decision_reason(gv.reason),
            )
        )
        # 组挂起时输出结构化 WARNING 日志（供告警平台捕获）
        if gv.decision == GroupDecision.GROUP_MANUAL:
            warning_text = build_group_warning_log(gv)
            self.log_warning(warning_text)
            logger.warning(warning_text)
        return gv

    def _write_trans_data(self, *, data: Any, trans_data: Any, gv: GroupVerdict, node_name: str) -> bool:
        """将 GroupVerdict 写回 trans_data 的两个静态字段 + data.outputs。

        无论本节点最终 return True / False，都先完整写入 trans_data：
          - 下游 cleanup Service 依据 group_verdict_decision 自行分支 no-op，不会误动作
          - DBA 重试时后续排查工具仍可读到本次判定上下文（evidence 完整保留）

        :param data: bamboo 节点数据对象
        :param trans_data: 当前节点 trans_data
        :param gv: 组决策结果
        :param node_name: 日志前缀用的节点名
        :return: True 写入成功；False 写入异常（理论不可达）
        """
        try:
            gv_dict: Dict[str, Any] = _group_verdict_to_dict(gv)
            if trans_data is not None:
                setattr(trans_data, "group_verdict", gv_dict)
                setattr(trans_data, "group_verdict_decision", gv.decision.value)
            data.outputs["trans_data"] = trans_data
            return True
        except Exception as err:
            self.log_error(_("[{}] 写入 trans_data 失败: {}").format(node_name, err))
            return False

    def _pre_declare_flow_summary(self, *, data: Any, gv: GroupVerdict, group: ResourceGroup) -> None:
        """GROUP_RECYCLE 判决下预申报 FlowSummary（全量写入本组 units）。

        设计意图：
          - 把 "决策产出 + 决策副产物（FlowSummary 落地）" 收敛在同一节点，避免散落到段 3；
          - 按 ``gv.verdicts`` 全量组装 summary_hosts；GROUP_RECYCLE 契约保证组内所有
            units 均需退回资源池，不做任何子状态过滤（例如不再按 F3 元数据残留筛子集）；
            语义为 "决策派发" 而非 "清理完成"。
          - 失败策略：insert_data 异常仅记 ERROR + logger.exception，不改判、不 return False；
            判决本身已成功产出，摘要表追加失败走人工兜底。

        :param data: bamboo 节点数据对象（用于取 global_data.job_root_id）
        :param gv: 组决策结果（必须是 GROUP_RECYCLE）
        :param group: 本组资源组（用于日志 group_id）
        """
        # GROUP_RECYCLE 契约：verdicts 覆盖本组所有 units，全量写入 FlowSummary
        summary_hosts: List[Dict[str, Any]] = [
            {
                "ip": v.unit.ip,
                "bk_host_id": v.unit.bk_host_id,
                "bk_cloud_id": v.unit.bk_cloud_id,
            }
            for v in gv.verdicts
        ]
        if not summary_hosts:
            # 防御性保护：GroupVerdict.__post_init__ 已校验 verdicts 数量 == group.units 数量，理论不可达
            return

        global_data: Dict[str, Any] = data.get_one_of_inputs("global_data") or {}
        # root_id 优先取 global_data["job_root_id"]（与旧惯例对齐），缺失回退 self.root_id
        root_id_for_summary: str = global_data.get("job_root_id") or self.root_id
        try:
            FlowOutputHandler(RecycleOutputContext.ToResourceSerializer).insert_data(
                root_id_for_summary, summary_hosts
            )
            self.log_info(
                _("[FlowSummary] 预申报本组待退回机器 {n} 台 · group_id={gid}").format(n=len(summary_hosts), gid=group.group_id)
            )
        except Exception as err:
            # insert_data 失败不阻塞主流程：判决已成功产出，仅摘要表追加失败
            self.log_error(
                _("[FlowSummary] 追加失败：{err} · group_id={gid} · 需人工确认摘要表").format(err=err, gid=group.group_id)
            )
            logger.exception(err)

    def _emit_manual_failure_log(self, gv: GroupVerdict) -> None:
        """GROUP_MANUAL 判决下输出失败引导日志（配合 _execute return False）。

        设计意图：
          - GROUP_MANUAL 的语义本就是 \"不能自动判断该否清理\"，需 DBA 介入
          - bamboo 尚未接入独立的 Pause 人工确认节点，目前用 return False 代替：
              * DBA 在 pipeline UI 看到判定节点 FAILED，点开可读到完整的单机日志块 + 组级结论
              * DBA 确认后可选：处置完外部问题后 \"重试\" / 直接 \"跳过\" 本节点
          - 该失败不影响已写入的 trans_data（_write_trans_data 已提前落盘）

        :param gv: 组决策结果（必须是 GROUP_MANUAL）
        """
        self.log_error(
            _(
                "\n{sep}\n"
                "本组判定结果为【整组挂起（GROUP_MANUAL）】，节点主动失败供人工确认\n"
                "  原因：{reason}\n"
                "  处置指引：\n"
                "    1) 查看上方单机日志块（标题行含主机 IP），确认具体异常机器\n"
                "    2) 外部频道处理异常（如手动摘除 DNS / 确认机器归属 / 手动清理残留进程）\n"
                "    3) 处理完后在 pipeline 上点击【重试】本节点；若确认无需回收可直接点击【跳过】\n"
                "{sep}"
            ).format(sep="━" * 60, reason=extract_decision_reason(gv.reason))
        )

    def log_warning(self, msg: str) -> None:
        """项目 BaseService 未提供 WARNING 级 log 助手，这里补一个基于 logger 的兜底。

        :param msg: 日志文本
        """
        logger.warning(msg)


class ResourceGroupJudgeComponent(Component):
    """组级判定汇聚 bamboo 组件。

    bamboo 组件包装层：把 :class:`ResourceGroupJudgeService` 挂到 pipeline 上，
    kwargs / trans_data 契约与判定决策逻辑详见 Service 类 docstring。

    上层建节点示例：
      act.component.inputs.kwargs = Var(type=Var.PLAIN, value={
          "group_dict": asdict(group),
          "ticket_id": ticket_id,
      })
    """

    name = __name__
    code = "resource_group_judge"
    bound_service = ResourceGroupJudgeService


# ==========================================================================
# ResourceGroup / GroupVerdict ↔ dict 互转辅助
# --------------------------------------------------------------------------
# 目的：bamboo pipeline 中 kwargs / trans_data 建议使用 pure dict / list / str /
# int / bool 等基本类型，避免跨节点序列化 dataclass 时的兼容性问题。
#
# 序列化：
#   - ResourceGroup 内部**无枚举字段**（``cluster_type`` 已在 Extractor 侧转为 str），
#     上游直接 ``dataclasses.asdict(group)`` 即可，无需任何包装函数
#   - :func:`_group_verdict_to_dict`：GroupVerdict 内含 FactState / HostDecision /
#     GroupDecision 三种枚举，asdict 保留枚举实例、无法跨 bamboo 节点 pickle，
#     故需 :func:`_stringify_enums` 递归替换为 ``.value`` 字符串
#
# 反序列化：
#   - ResourceGroup 侧统一走 :meth:`ResourceGroup.from_dict`（models.py 内定义），
#     与 ``asdict`` 对称；嵌套子对象反序列化委派给 :meth:`RevokeUnit.from_dict` /
#     :meth:`AccessLayerInstance.from_dict`，职责归位到 dataclass 自身契约
#   - GroupVerdict 侧只做出参（trans_data 写入 pure dict），无需反序列化入口
# ==========================================================================


def _group_verdict_to_dict(gv: GroupVerdict) -> Dict[str, Any]:
    """将 :class:`GroupVerdict` 序列化为 pure dict，供 trans_data 传递。

    业务动因：GroupVerdict 内嵌 FactState / HostDecision / GroupDecision 三种枚举，
    ``dataclasses.asdict`` 保留枚举实例、无法跨 bamboo 节点 pickle，故先 asdict 展开再
    委托 :func:`_stringify_enums` 递归替换为枚举的 ``.value`` 字符串。

    :param gv: 组级判定结果对象
    :return: 稳定结构的 dict
    """
    # 使用 dataclasses.asdict 会递归转所有 dataclass；枚举类型需要额外处理为 value
    raw = asdict(gv)
    return _stringify_enums(raw)


def _stringify_enums(node: Any) -> Any:
    """递归把 dict / list 中的枚举实例替换为其 value 字符串。

    业务动因：:class:`FactState` / :class:`HostDecision` / :class:`GroupDecision` 三种枚举
    无法跨 bamboo 节点 pickle，写入 trans_data 前必须替换为字符串；单独抽出通用递归函数以便复用。

    :param node: 任意 dict / list / 标量
    :return: 同构结构但枚举全部替换为 value
    """
    if isinstance(node, dict):
        return {k: _stringify_enums(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_stringify_enums(x) for x in node]
    # 枚举类型判断（FactState / HostDecision / GroupDecision 都是 Enum 子类）
    if isinstance(node, Enum):
        return node.value
    return node
