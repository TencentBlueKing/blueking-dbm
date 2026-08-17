# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主机退回资源池 · 日志 / 节点名格式化辅助模块。

模块职责：
  - 为 `resource_group_revoke_subflow` / `group_judge` / `group_cleanup` 三处提供
    **统一的 IP 列表格式化 + 决策代号中文化**工具
  - 输出既用于 bamboo `act_name` / `sub_name`，也用于 Service 内日志的主标识

设计要点：
  - **不折叠 IP**：完整列出全部 IP（用 `, ` 分隔），保证 DBA 在流程节点树 / 日志里
    能看到所有涉及的机器；bamboo 前端已支持横向滚动，长文案不是问题
  - **代号中文化**：`SKIP / KEEP / RECYCLE / MANUAL` 等内部代号只在源码 / 告警关键字
    里保留，面向用户日志一律用中文短语（配合原代号括号注明，便于人工排查跨模块 grep）
  - **`extract_decision_reason` 剥离代号前缀**：`verdict.reason` 里携带的 `决策=SKIP：`
    这类前缀是给告警平台看的，日志里应只输出后半段"业务原因"
  - **本模块不做空校验**：空 units 场景由上层的 RevokeFlowBaseException 拦截

边界：
  - 空 units -> 返回空字符串 `""`（不 raise，交由上层判断）
  - 未知代号 -> 直接回退为代号原文（不 raise），避免因文案漏映射导致节点失败
"""
from typing import TYPE_CHECKING

from django.utils.translation import gettext as _

if TYPE_CHECKING:
    # 仅类型注解使用；运行时不导入以避免循环 import
    from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import ResourceGroup


#: 单机决策代号 → 中文短语映射（面向 DBA / SRE 阅读日志）
#: 对应 :class:`HostDecision` 的 4 个 value；命中不到时回退代号原文
HOST_DECISION_ZH: dict = {
    "skip": _("跳过（不属于本单据）"),
    "keep": _("保留（仍在服务）"),
    "recycle": _("可清理"),
    "manual": _("挂起（需人工确认）"),
}

#: 组决策代号 → 中文短语映射（面向 DBA / SRE 阅读日志）
#: 对应 :class:`GroupDecision` 的 4 个 value；命中不到时回退代号原文
GROUP_DECISION_ZH: dict = {
    "group_skip": _("整组跳过"),
    "group_keep": _("整组保留"),
    "group_recycle": _("整组清理"),
    "group_manual": _("整组挂起"),
}


def format_group_ips(group: "ResourceGroup") -> str:
    """将组内 IP 列表格式化为 `, ` 分隔的完整字符串（供 act_name / 日志共用）。

    功能说明：
      - 展开 `group.units` 提取 IP 列表，保留原始顺序
      - 全部 IP 完整列出，不折叠、不省略（DBA 需要看到所有涉及机器）
      - IP 之间用 `, ` 分隔（含空格，方便终端 / 前端换行显示时断词）

    :param group: 资源组；由 Extractor 保证 `group.units` 保序
    :return: 逗号空格分隔的 IP 列表字符串；空 units 场景返回 `""`

    边界：
      - `group.units` 为空 -> 返回空串（上层已在 build_group_revoke_subflow 处
        用 RevokeFlowBaseException 拦截，本函数不做额外空校验）
      - IP 数量为 1 -> 直接展示单 IP

    示例：
      >>> format_group_ips(group_with_1_unit)
      '1.1.1.1'
      >>> format_group_ips(group_with_4_units)
      '1.1.1.1, 2.2.2.2, 3.3.3.3, 4.4.4.4'
    """
    if not group.units:
        return ""
    return ",\n ".join(u.ip for u in group.units)


def host_decision_zh(decision_value: str) -> str:
    """把单机决策代号（:class:`HostDecision` 的 .value）转成中文短语；未知代号回退原文。"""
    return HOST_DECISION_ZH.get(decision_value, decision_value)


def group_decision_zh(decision_value: str) -> str:
    """把组决策代号（:class:`GroupDecision` 的 .value）转成中文短语；未知代号回退原文。"""
    return GROUP_DECISION_ZH.get(decision_value, decision_value)


def extract_decision_reason(reason: str) -> str:
    """从 `verdict.reason` / `group_verdict.reason` 中剥离"决策=X："前缀 + 清洗 F/G 代号。

    功能说明：
      - :class:`HostDecisionMatrix` 与 :class:`GroupDecisionMatrix` 产出的 reason 形如
        ``"决策=RECYCLE：F1=YES F2=NO F4=no，按 F3 evidence 精确清理"``
        ``"组决策=GROUP_MANUAL：G1=NO 组内单机结论不一致..."``
      - 面向用户日志里代号已单独中文化展示，reason 里再出现 F1/F2/F3/F4/G1/G2 是噪音
      - 本函数分两步清洗：
          1) 按"首个中文冒号 `：`"切分，取右侧作为业务原因（剥离 `决策=X：` 前缀）
          2) 用固定映射把 reason 里的 F/G 代号替换为业务白话

    :param reason: 原始 reason 字符串
    :return: 剥离前缀 + 清洗代号后的业务原因；未匹配前缀时对原文做代号清洗后返回

    示例：
      >>> extract_decision_reason("决策=RECYCLE：F1=YES F2=NO F4=no，按 F3 evidence 精确清理")
      '归属本单据，无 DNS/CLB 绑定，无进程，按元数据残留证据精确清理'
      >>> extract_decision_reason("组决策=GROUP_MANUAL：G1=NO 组内单机结论不一致")
      '组内结论不一致'
    """
    if not reason:
        return ""
    # 步骤 1：剥离前缀（"决策=X：" / "组决策=Y："）
    idx = reason.find("：")
    body = reason[idx + 1 :].strip() if idx >= 0 else reason

    # 步骤 2：F/G 代号 → 业务白话（顺序敏感：先长后短，避免部分匹配）
    # 说明：这里的替换只影响面向用户的日志输出，不影响 verdict.reason 原文
    #      （告警平台 / 单测 grep 仍可用原代号定位）
    replacements: list = [
        # G 判据（放最前，避免被 F 判据模式误匹配）
        ("G1=YES", _("组内结论一致")),
        ("G1=NO", _("组内结论不一致")),
        ("G1=UNKNOWN", _("组内一致性未知")),
        # F 判据
        ("F1=YES", _("归属本单据")),
        # F1=NO 的真实成因是广义集合（MachineEvent 缺失 / CC 查不到 / 被别的合法单接管 /
        # CC 模块处于混合状态 / 真·被挪到其他业务），不应断言成"非法移动"这一具象成因
        ("F1=NO", _("不归属本单据（可能被挪走/被接管/事件缺失）")),
        ("F1=UNKNOWN", _("归属状态未知")),
        ("F2=YES", _("有 DNS/CLB 绑定")),
        ("F2=NO", _("无 DNS/CLB 绑定")),
        ("F2=UNKNOWN", _("DNS/CLB 绑定状态未知")),
        ("F3=YES", _("有元数据残留")),
        ("F3=NO", _("无元数据残留")),
        ("F3=UNKNOWN", _("元数据残留状态未知")),
        ("F4=YES", _("进程存活")),
        ("F4=NO", _("无进程")),
        ("F4=UNKNOWN", _("进程状态未知")),
        # 兼容 decision.py 里对 F4 小写 yes/no（历史遗留写法）
        ("F4=yes", _("进程存活")),
        ("F4=no", _("无进程")),
        # 固定短语（放最后，避免 F3 代号已被替换后再匹配失效）
        (_("按 F3 evidence 精确清理"), _("按元数据残留证据精确清理")),
    ]
    for old, new in replacements:
        body = body.replace(old, new)
    return body


# ==========================================================================
# F/G 判据 state 值 → 业务白话映射（供单机日志"检测项"段落使用）
# --------------------------------------------------------------------------
# 使用场景：面向用户的判据结果输出（"是 / 否 / 未知" 三态白话），配合固定检测项
# 名称一起展示，让 DBA / SRE 一眼看懂"检测了什么、结果如何"，避免代号泄露。
# 输入统一为 :class:`FactState` 的 .value 字符串（yes / no / unknown），
# 未知代号 fail-safe 回退代号原文。
# ==========================================================================


#: F1 · 是否归属本单据的主机
#: 正向映射（与判据语义一致，不再反转）：
#:   state=YES（归属本单）→ "是"
#:   state=NO（不归属本单，广义集合：事件缺失/CC 查不到/被合法接管/混合模块/真·非法移动）→ "否"
F1_STATE_ZH: dict = {
    "yes": _("是"),
    "no": _("否"),
    "unknown": _("未知"),
}

#: F2 · 是否绑定 DNS 或 CLB 服务
#: state=YES 表示"有 DNS/CLB 引用（红线）" -> "是"
#: state=NO 表示"无 DNS/CLB 引用" -> "否"
F2_STATE_ZH: dict = {
    "yes": _("是"),
    "no": _("否"),
    "unknown": _("未知"),
}

#: F3 · 是否有元数据残留
#: state=YES 表示"存在元数据残留" -> "有"
F3_STATE_ZH: dict = {
    "yes": _("有"),
    "no": _("无"),
    "unknown": _("未知"),
}

#: F4 · 进程是否存活
#: state=YES 表示"本单端口进程仍在跑" -> "有"
F4_STATE_ZH: dict = {
    "yes": _("有"),
    "no": _("无"),
    "unknown": _("未知"),
}

#: G1 · 组内单机结论一致性
G1_STATE_ZH: dict = {
    "yes": _("一致"),
    "no": _("不一致"),
    "unknown": _("未知"),
}


def f1_zh(state_value: str) -> str:
    """F1 · 是否归属本单据的主机 · state → 白话（"是" / "否" / "未知"）；未知代号回退原文。"""
    return F1_STATE_ZH.get(state_value, state_value)


def f2_zh(state_value: str) -> str:
    """F2 · 是否绑定 DNS 或 CLB 服务 · state → 白话（"是" / "否" / "未知"）；未知代号回退原文。"""
    return F2_STATE_ZH.get(state_value, state_value)


def f3_zh(state_value: str) -> str:
    """F3 · 是否有元数据残留 · state → 白话（"有" / "无" / "未知"）；未知代号回退原文。"""
    return F3_STATE_ZH.get(state_value, state_value)


def f4_zh(state_value: str) -> str:
    """F4 · 进程是否存活 · state → 白话（"有" / "无" / "未知"）；未知代号回退原文。"""
    return F4_STATE_ZH.get(state_value, state_value)


def g1_zh(state_value: str) -> str:
    """G1 · 组内单机结论一致性 · state → 白话（"一致" / "不一致" / "未知"）；未知代号回退原文。"""
    return G1_STATE_ZH.get(state_value, state_value)


# ==========================================================================
# F2 · 检测项标题的"按 role 路由"（与 check_f2_traffic 的 3 条判据路径一一对应）
# --------------------------------------------------------------------------
# 使用场景：单机日志的检测项 ② 标题；根据 unit.role 匹配 F2 实际跑的判据路径，
# 输出贴切语义的检测项名称，避免对 BACKEND_MASTER / REMOTE_MASTER 等角色错误
# 展示 "是否绑定 DNS 或 CLB 服务"（这些角色根本不挂 DNS/CLB）。
#
# 角色集与 host_check.py 中 _F2C_APPLICABLE_ROLES / _F2D_APPLICABLE_ROLES 并行
# 维护：此处面向"日志展示"，host_check 面向"判据路由"，语义不同但枚举值相同；
# 若 host_check 新增角色路由，本模块需同步补充（通过默认分支 fail-safe 兜底）。
# ==========================================================================

#: F2.c · tdbctl 中控路由子判据覆盖的角色集（TenDBCluster REMOTE 存储层）
#: 对应 :class:`InstanceRole` 的 REMOTE_MASTER / REMOTE_SLAVE / REMOTE_REPEATER
_F2C_ROLES_FOR_LOG: frozenset = frozenset({"remote_master", "remote_slave", "remote_repeater"})

#: F2.d · proxy 后端引用子判据覆盖的角色集（TenDBHA BACKEND 存储层）
#: 对应 :class:`InstanceRole` 的 BACKEND_MASTER / BACKEND_REPEATER（slave 走 DNS 不走此路径）
_F2D_ROLES_FOR_LOG: frozenset = frozenset({"backend_master", "backend_repeater"})

#: F2 检测项标题 · 按判据路径分类
#: - F2.c 路径（REMOTE_*）：被 tdbctl 中控 mysql.servers 路由引用
#: - F2.d 路径（BACKEND_MASTER / BACKEND_REPEATER）：被 proxy 作为后端引用
#: - F2.a + F2.b 路径（其他）：绑定 DNS / CLB 服务
F2_TITLE_BY_PATH: dict = {
    "f2c": _("是否被 tdbctl 中控路由引用  "),
    "f2d": _("是否被 proxy 作为后端引用   "),
    "f2ab": _("是否绑定 DNS 或 CLB 服务   "),
}


def f2_title_by_role(role: str) -> str:
    """F2 · 按 role 返回检测项 ② 的中文标题（对齐 check_f2_traffic 的策略路由）。

    功能说明：
      按 ``unit.role`` 匹配 F2 的 3 条判据路径（F2.c / F2.d / F2.a+F2.b）输出贴合语义
      的检测项标题；返回标题末尾已对齐字符宽度，便于日志块内对齐冒号。

    :param role: :class:`InstanceRole` 的 .value（小写字符串，如 ``backend_master``）
    :return: 中文检测项标题（含尾部对齐空格）；未知 role → 回退 F2.a+F2.b 标题（fail-safe，
             兼容 PROXY / SPIDER / ORPHAN / BACKEND_SLAVE / SPIDER_SLAVE / SPIDER_MNT 等）

    示例：
      >>> f2_title_by_role("backend_master")
      '是否被 proxy 作为后端引用   '
    """
    if role in _F2C_ROLES_FOR_LOG:
        return F2_TITLE_BY_PATH["f2c"]
    if role in _F2D_ROLES_FOR_LOG:
        return F2_TITLE_BY_PATH["f2d"]
    return F2_TITLE_BY_PATH["f2ab"]
