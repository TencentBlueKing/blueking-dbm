# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主机退回资源池 · 组级 G 判据采集器。

模块职责：
  - :class:`ResourceGroupChecker` 提供组级 G1 判据（组内一致性）采集方法，纯本地聚合无 IO
  - 判据结果统一为 :class:`FactCheckOutcome`，供 :class:`GroupDecisionMatrix` 消费

设计要点：
  - G1 是纯函数：仅依赖组内单机 verdict，可 100% 单测
  - 单一职责：G 判据只做采集，决策映射交给 :class:`GroupDecisionMatrix`

模块边界：
  - 本模块不做清理动作，不修改任何元数据
"""
import logging
from typing import Dict, List, Tuple

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import (
    FactCheckOutcome,
    FactState,
    GroupVerdict,
    RevokeVerdict,
)

logger = logging.getLogger("flow")


class ResourceGroupChecker:
    """组级 G 判据采集器。

    职责：
      - 汇总组内单机 verdict 产出 G1 判据（组内一致性）

    使用方式：
      checker = ResourceGroupChecker(root_id="root-xxx")
      g1 = checker.check_g1_consistency(verdicts)

    线程安全：是（无实例可变状态）
    边界：
      - verdicts 为空 -> G1 判 UNKNOWN（不能确认一致性）
    """

    def __init__(self, root_id: str) -> None:
        """:param root_id: flow root_id，用于日志追踪"""
        self.root_id: str = root_id

    # ---------------- G1 · 组内一致性 ----------------

    def check_g1_consistency(self, verdicts: Tuple[RevokeVerdict, ...]) -> FactCheckOutcome:
        """G1 · 组内一致性判据：组内所有机器结论完全一致则 YES。

        怎么做：
          - 收集组内所有单机 decision，若全部相等 → YES
          - 否则 → NO，evidence 记录具体构成

        :param verdicts: 组内单机 RevokeVerdict 序列
        :return: :class:`FactCheckOutcome`
        边界：
          - verdicts 为空 -> UNKNOWN（无法判定组一致性）
          - 全部一致（含全 MANUAL 的情况）也算 YES，但 GroupDecisionMatrix 会把
            "全 MANUAL 的 G1=YES" 视作"组内出现 MANUAL"（结论不属于 SKIP/KEEP/RECYCLE 三种），
            通过决策矩阵兜底走 GROUP_MANUAL
        """
        if not verdicts:
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                evidence={"reason": "verdicts is empty"},
                error="verdicts is empty",
                reason=_("G1=UNKNOWN：组内无 verdict，无法判定一致性"),
            )

        decisions = [v.decision for v in verdicts]
        first = decisions[0]
        all_same = all(d == first for d in decisions)
        # 统计各结论数量，供 evidence 展示
        counter: Dict[str, int] = {}
        for d in decisions:
            counter[d.value] = counter.get(d.value, 0) + 1

        if all_same:
            return FactCheckOutcome(
                state=FactState.YES,
                evidence={"construction": counter, "unified_decision": first.value},
                reason=_("G1=YES：组内 {} 台机器结论一致（{}）").format(len(verdicts), first.value),
            )
        return FactCheckOutcome(
            state=FactState.NO,
            evidence={"construction": counter},
            reason=_("G1=NO：组内单机结论不一致，构成 {}").format(counter),
        )


def build_group_warning_log(gv: GroupVerdict) -> str:
    """基于 GroupVerdict 生成 GROUP_MANUAL 场景下的结构化 WARNING 日志文本。

    职责：
      - 需求 6.3 / 10.4 · 组挂起时输出的告警日志内容
      - 便于告警平台按关键字捕获

    :param gv: 组级判定结论对象
    :return: 多行结构化日志字符串
    """
    lines: List[str] = []
    lines.append(
        "[REVOKE_GROUP_MANUAL] group_id={} decision={} reason={}".format(
            gv.group.group_id, gv.decision.value, gv.reason
        )
    )
    lines.append("  G1: state={} reason={}".format(gv.g1.state.value, gv.g1.reason))
    for v in gv.verdicts:
        lines.append(
            "  host ip={} bk_host_id={} role={} decision={} F1={} F2={} F3={} F4={} reason={}".format(
                v.unit.ip,
                v.unit.bk_host_id,
                v.unit.role,
                v.decision.value,
                v.facts.f1_ownership.state.value,
                v.facts.f2_traffic.state.value,
                v.facts.f3_dbm_residue.state.value,
                v.facts.f4_process.state.value,
                v.reason,
            )
        )
    return "\n".join(lines)
