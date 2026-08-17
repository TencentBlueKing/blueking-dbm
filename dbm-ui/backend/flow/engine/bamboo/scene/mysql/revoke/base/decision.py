# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主机退回资源池 · 决策矩阵纯函数集合。

模块职责：
  - :class:`HostDecisionMatrix` 将单机 F1~F4 判据映射为 SKIP/KEEP/MANUAL/RECYCLE 单机结论
  - :class:`GroupDecisionMatrix` 将 G1 + G2 + 组内单机结论映射为 GROUP_* 组结论

设计要点：
  - **纯函数、无 IO、无副作用**：所有 classmethod 只做条件判断与对象组装，可 100% 单元测试
  - **严格对齐需求文档**：单机决策表见需求文档 表 2（11 行），组决策表见需求文档 表 4（8 行）
  - **UNKNOWN 保守偏向**：F1 UNKNOWN → SKIP（不属于本单）；F2 UNKNOWN → MANUAL（红线保守挂起）；
    F4 UNKNOWN → MANUAL（进程未知不敢清理）；F3 UNKNOWN → 视清理需要与 F4 组合决定
  - **决策原因文本化**：每个决策都携带 reason 字符串，便于日志与人工排查

模块边界：
  - 本模块只做决策，不做判据采集
  - 判据采集在 host_check.py / group_check.py 中实现
"""
from typing import List, Tuple

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import (
    FactCheckOutcome,
    FactState,
    GroupDecision,
    GroupVerdict,
    HostDecision,
    HostRevokeFacts,
    ResourceGroup,
    RevokeUnit,
    RevokeVerdict,
)


class HostDecisionMatrix:
    """单机决策矩阵 · F1~F4 → SKIP/KEEP/MANUAL/RECYCLE。

    职责：
      - 严格按需求文档"组决策判断表 · 表 2"的 11 行组合产出单机结论
      - 挂载 evidence 与决策 reason 到返回的 :class:`RevokeVerdict`
      - 纯函数、无副作用，可单测

    使用方式：
        verdict = HostDecisionMatrix.classify(unit, facts)

    线程安全：是（无实例状态）
    边界：
      - unit / facts 类型不匹配 -> :class:`RevokeUnit` / :class:`HostRevokeFacts` 构造器已校验
    """

    @classmethod
    def classify(cls, unit: RevokeUnit, facts: HostRevokeFacts) -> RevokeVerdict:
        """按决策矩阵产出单机结论。

        判定顺序：
          1) F1=NO / UNKNOWN → SKIP（短路）
          2) F1=YES 后再看 F2 + F3 + F4 组合

        :param unit: 判定所属机器单元
        :param facts: 单机 F1~F4 判据快照
        :return: :class:`RevokeVerdict`
        边界：
          - 未匹配任何决策矩阵格子（理论不可能） -> 兜底判 MANUAL 并携带原因
        """
        # ---- Step 1：F1 短路 ----
        if facts.f1_ownership.state != FactState.YES:
            reason_suffix = "F1=UNKNOWN" if facts.f1_ownership.state == FactState.UNKNOWN else "F1=NO"
            return RevokeVerdict(
                unit=unit,
                decision=HostDecision.SKIP,
                facts=facts,
                reason=_("决策=SKIP：{}，机器已不属于本单据").format(reason_suffix),
            )

        # ---- Step 2：F1=YES 后按 F2/F3/F4 组合 ----
        f2 = facts.f2_traffic.state
        f3 = facts.f3_dbm_residue.state
        f4 = facts.f4_process.state

        # F2=UNKNOWN → 红线判据不确定，保守挂起（表 2 第 6 行）
        if f2 == FactState.UNKNOWN:
            return RevokeVerdict(
                unit=unit,
                decision=HostDecision.MANUAL,
                facts=facts,
                reason=_("决策=MANUAL：F2 红线判据无法确认，为安全起见挂起等 DBA 排查"),
            )

        # F2=YES → 红线，永不清理（表 2 第 2~5 行）
        if f2 == FactState.YES:
            if f3 == FactState.YES and f4 == FactState.YES:
                return RevokeVerdict(
                    unit=unit,
                    decision=HostDecision.KEEP,
                    facts=facts,
                    reason=_("决策=KEEP：F2=YES 红线保留，元数据完整且进程正常，正在服务"),
                )
            # F2=YES 但 F3/F4 不完整 → 数据异常，MANUAL
            if f3 == FactState.NO:
                return RevokeVerdict(
                    unit=unit,
                    decision=HostDecision.MANUAL,
                    facts=facts,
                    reason=_("决策=MANUAL：F2=YES 在服务但 F3=NO DBM 无残留，数据一致性异常"),
                )
            if f4 == FactState.NO:
                return RevokeVerdict(
                    unit=unit,
                    decision=HostDecision.MANUAL,
                    facts=facts,
                    reason=_("决策=MANUAL：F2=YES 在服务但 F4=NO 进程挂，需 DBA 排查"),
                )
            if f4 == FactState.UNKNOWN:
                return RevokeVerdict(
                    unit=unit,
                    decision=HostDecision.MANUAL,
                    facts=facts,
                    reason=_("决策=MANUAL：F2=YES 在服务但 F4=UNKNOWN 进程状态未知"),
                )
            # F3=UNKNOWN 但 F2=YES 且 F4=YES → 保守当 MANUAL（元数据未知不能确认闭合性）
            if f3 == FactState.UNKNOWN:
                return RevokeVerdict(
                    unit=unit,
                    decision=HostDecision.MANUAL,
                    facts=facts,
                    reason=_("决策=MANUAL：F2=YES 在服务但 F3=UNKNOWN 元数据未知"),
                )
            # 兜底（理论不可达）
            return RevokeVerdict(
                unit=unit,
                decision=HostDecision.MANUAL,
                facts=facts,
                reason=_("决策=MANUAL：F2=YES 分支未匹配矩阵已定义组合，保守挂起"),
            )

        # F2=NO 后 → 一律 RECYCLE 或 MANUAL（表 2 第 7~11 行）
        # F4=UNKNOWN → MANUAL（不敢自动清理机器进程）
        if f4 == FactState.UNKNOWN:
            return RevokeVerdict(
                unit=unit,
                decision=HostDecision.MANUAL,
                facts=facts,
                reason=_("决策=MANUAL：F2=NO 但 F4=UNKNOWN 进程状态未知，不敢自动清理"),
            )

        # F4 = YES 或 NO 都视为可回收；F3 决定要清多少东西
        return RevokeVerdict(
            unit=unit,
            decision=HostDecision.RECYCLE,
            facts=facts,
            reason=_("决策=RECYCLE：F1=YES F2=NO F4={}，按 F3 evidence 精确清理").format(f4.value),
        )


class GroupDecisionMatrix:
    """组级决策矩阵 · G1 + 组内单机结论 → GROUP_*。

    职责：
      - 严格按需求文档"组决策判断表 · 表 4"的组合产出组结论
      - 组挂起（GROUP_MANUAL）时 reason 携带完整挂起原因文本

    使用方式：
        gv = GroupDecisionMatrix.classify(group, verdicts, g1)

    线程安全：是
    边界：
      - verdicts 数量与 group.units 数量不一致 -> GroupVerdict 构造器会 raise
    """

    @classmethod
    def classify(
        cls,
        group: ResourceGroup,
        verdicts: Tuple[RevokeVerdict, ...],
        g1: FactCheckOutcome,
    ) -> GroupVerdict:
        """按组决策矩阵产出组结论。

        决策顺序：
          1) G1=NO（组内混合结论）→ GROUP_MANUAL
          2) G1=YES 且组内均 SKIP → GROUP_SKIP
          3) G1=YES 且组内均 KEEP → GROUP_KEEP
          4) G1=YES 且组内均 RECYCLE → GROUP_RECYCLE

        :param group: 判定所属资源组
        :param verdicts: 组内每台机器的单机 RevokeVerdict（顺序需对应 group.units）
        :param g1: G1 组内一致性判据结果
        :return: :class:`GroupVerdict`
        边界：
          - g1 类型不匹配 -> GroupVerdict 构造器会 raise
          - 组内混合结论（含 MANUAL / RECYCLE+KEEP 等）走 GROUP_MANUAL，reason 说明具体构成
        """
        # ---- Step 1: G1=NO → GROUP_MANUAL ----
        if g1.state != FactState.YES:
            construction = cls._describe_construction(verdicts)
            return GroupVerdict(
                group=group,
                decision=GroupDecision.GROUP_MANUAL,
                verdicts=verdicts,
                g1=g1,
                reason=_("组决策=GROUP_MANUAL：G1=NO 组内单机结论不一致，构成 {}").format(construction),
            )

        # ---- Step 2: G1=YES → 看组内单机结论 ----
        decisions = [v.decision for v in verdicts]

        if all(d == HostDecision.SKIP for d in decisions):
            return GroupVerdict(
                group=group,
                decision=GroupDecision.GROUP_SKIP,
                verdicts=verdicts,
                g1=g1,
                reason=_("组决策=GROUP_SKIP：组内全部机器均为 SKIP，本组不属于本单据"),
            )

        if all(d == HostDecision.KEEP for d in decisions):
            return GroupVerdict(
                group=group,
                decision=GroupDecision.GROUP_KEEP,
                verdicts=verdicts,
                g1=g1,
                reason=_("组决策=GROUP_KEEP：组内全部机器均为 KEEP，红线保留整组"),
            )

        if all(d == HostDecision.RECYCLE for d in decisions):
            return GroupVerdict(
                group=group,
                decision=GroupDecision.GROUP_RECYCLE,
                verdicts=verdicts,
                g1=g1,
                reason=_("组决策=GROUP_RECYCLE：组内全部机器均为 RECYCLE"),
            )

        # 兜底（理论不可达：G1=YES 意味着结论一致，上面三种情况已覆盖）
        construction = cls._describe_construction(verdicts)
        return GroupVerdict(
            group=group,
            decision=GroupDecision.GROUP_MANUAL,
            verdicts=verdicts,
            g1=g1,
            reason=_("组决策=GROUP_MANUAL：G1=YES 但组内结论构成异常 {}，兜底挂起").format(construction),
        )

    @staticmethod
    def _describe_construction(verdicts: Tuple[RevokeVerdict, ...]) -> str:
        """组装组内结论构成的可读描述。

        :param verdicts: 组内单机 verdict 序列
        :return: 形如 "{RECYCLE=2, KEEP=1, MANUAL=0, SKIP=0}"
        """
        counter = {d.value: 0 for d in HostDecision}
        for v in verdicts:
            counter[v.decision.value] = counter.get(v.decision.value, 0) + 1
        parts: List[str] = ["{}={}".format(k, v) for k, v in counter.items()]
        return "{" + ", ".join(parts) + "}"
