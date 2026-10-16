# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主机退回资源池 · 一组资源的退回子流程（"计算 + 清理" 合并到同一 SubProcess）。

模块职责：
  - 暴露 :func:`build_group_revoke_subflow` 供顶层 revoke_flow 编排"每组一个子流程"
  - 4 段串行编排（均在同一 SubProcess 内运行，共享同一份 ``trans_data``）：
      1) 单 act 下发 :class:`MySQLHostProcessCheckComponent`（多 IP 一次 Job + APPEND 模式），
         产出 ``trans_data.host_process_check`` = ``{ip: <ctx_dict>}``
      2) :class:`ResourceGroupJudgeComponent`：读段 1 + 跑 F1~F4 + G1/G2 + 决策矩阵，
         产出 ``trans_data.group_verdict`` + ``trans_data.group_verdict_decision``；
         GROUP_RECYCLE 判决产出瞬间同步写入 FlowSummary（预申报语义，而非清理完成台账）
      3) :class:`ResourceGroupCleanupComponent`：按 verdict evidence 精确清元数据；
         不写 trans_data、不写 FlowSummary（职责纯粹化）
      4) :class:`ResourceGroupMachineClearComponent`：自主基于 ``trans_data.group_verdict``
         筛选 F4=yes 的 IP 作为 exec_ips，空则 no-op；不再依赖 ``pending_clear_ips`` 字段

设计要点：
  - **合并为单 SubProcess 是必需的**：bamboo SubProcess 之间 ``trans_data`` 无法回写，
    段 1 / 段 2 写入的字段在跨 SubProcess 时读不到；同 SubProcess 内则天然可传
  - **静态字段名 + SubProcess 隔离**：每组一个独立 SubProcess，各自持有独立的
    :class:`RevokeTransData` 副本 → 字段用**静态名**（无需 ``__{group_id}`` 后缀）
    组间字段互不干扰，契约清晰、可静态检查
  - **段 1 从"并行 N 台 act"塌陷为"单 act 多 IP"**：BK Job 天然支持多 IP 一次下发，
    节省 N-1 次 Job 实例创建 + 状态轮询开销，pipeline 拓扑更清晰
  - **APPEND 写入模式**（``kwargs["write_op"] = WriteContextOpType.APPEND.value``）：
    段 1 完成后 ``trans_data.host_process_check`` = ``{ip: <ctx>}``；
    段 2 判定 Service 按 IP 索引即可
  - **节点名 / 日志主标识使用组内 IP 列表**（:func:`format_group_ips`）：
    DBA 从 bamboo 引擎控制台可直接看到本 act 处理的机器集合；``group.group_id``
    仅在数据结构和告警日志（``[REVOKE_GROUP_MANUAL]``）中保留，不进用户可见 act 文案
  - **不引入 Pause 节点**：即使组决策为 GROUP_MANUAL，段 3 会 no-op、段 4 也会 no-op；
    Pause 由顶层单据引擎决定，本子流程只做"决定并动手"

模块边界：
  - group.units 为空 -> raise（Extractor 已保证非空，此处兜底）
  - group.group_id 为空 -> raise（Extractor 保证生成 apply_info_{idx}）
  - global_data 缺 bk_biz_id -> raise（顶层 _do_revoke_flow 已保证传入）
  - 中间任一步失败：判定/清理 Service 内已改判 GROUP_MANUAL，pipeline 依然正常结束
"""
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend.flow.consts import DBA_ROOT_USER, WriteContextOpType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.revoke.base.log_utils import format_group_ips
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import ResourceGroup
from backend.flow.engine.revoke.exception import RevokeFlowBaseException
from backend.flow.plugins.components.collections.mysql.host_process_check import MySQLHostProcessCheckComponent
from backend.flow.plugins.components.collections.mysql.revoke.group_cleanup import (
    ResourceGroupCleanupComponent,
    ResourceGroupMachineClearComponent,
)
from backend.flow.plugins.components.collections.mysql.revoke.group_judge import ResourceGroupJudgeComponent

#: MySQL 家族进程白名单：F4 判据的默认扫描目标（覆盖 mysqld / mysql-proxy / mariadbd）
_DEFAULT_PROCESS_WHITELIST: List[str] = ["mysqld", "mysql-proxy", "mariadbd"]


def build_group_revoke_subflow(
    root_id: str,
    ticket_id: int,
    group: ResourceGroup,
    global_data: Optional[Dict[str, Any]] = None,
) -> SubProcess:
    """构建一组资源的"退回子流程"（4 段串行合并到单 SubProcess）。

    :param root_id: bamboo root pipeline id
    :param ticket_id: 当前 revoke 所属的原单据 id，供 F1 所有权判据使用
    :param group: 待处理的 :class:`ResourceGroup`；组内 units 必须同云区域（部署单 apply_info 天然满足）
    :param global_data: 子流程全局数据；由顶层 revoke_flow 组装，
        **必须包含**：``uid`` / ``ticket_id`` / ``bk_biz_id`` / ``db_type`` / ``os_type``。
        本函数不再对这些字段做 setdefault 兜底（顶层已保证传入）。
    :return: :class:`SubProcess` 子流程对象，交给顶层 Builder.add_parallel_sub_pipeline 使用

    边界：
      - group.units 为空 -> raise :class:`RevokeFlowBaseException`
      - global_data 缺 bk_biz_id -> raise :class:`RevokeFlowBaseException`
      - 组内多云区域 -> 只取第 0 台的 bk_cloud_id（Extractor 保证组内同云）
      - group.group_id 空校验由 :meth:`ResourceGroup.__post_init__` 在构造期拦截，本处不再重复
    """
    if not group.units:
        raise RevokeFlowBaseException(
            "build_group_revoke_subflow: group.units is empty (group_id={})".format(group.group_id)
        )

    # 顶层 global_data 契约由 _do_revoke_flow 保证；本处仅做一层不变量断言
    sub_data: Dict[str, Any] = dict(global_data or {})
    if "bk_biz_id" not in sub_data:
        raise RevokeFlowBaseException(
            "build_group_revoke_subflow: global_data.bk_biz_id is required (group_id={})".format(group.group_id)
        )

    sub_pipeline = SubBuilder(root_id=root_id, data=sub_data)

    # 组内所有 IP + 共享云区域（约束：组内同云；Extractor 已保证）
    exec_ips: List[str] = [u.ip for u in group.units]
    bk_cloud_id: int = int(group.units[0].bk_cloud_id)

    # 生成节点名 / 日志共用的 IP 列表字符串（全量展示，`, ` 分隔，不折叠）
    ips_display: str = format_group_ips(group)

    # ---- 段 1：单 act 多 IP 下发进程扫描（APPEND 模式汇聚为 {ip: <ctx>}）----
    sub_pipeline.add_act(
        act_name=_("进程扫描 [{ips}]").format(ips=ips_display),
        act_component_code=MySQLHostProcessCheckComponent.code,
        kwargs={
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": exec_ips,  # List[str]，父类 splice_exec_ips_list 内部会展开
            "expected_proc_names": _DEFAULT_PROCESS_WHITELIST,
            "account_alias": DBA_ROOT_USER,
            # 关键：APPEND 模式让每台机器的 <ctx> 汇聚为 {ip: <ctx>}，
            # 而不是最后一台覆盖前面所有（REWRITE 语义）
            "write_op": WriteContextOpType.APPEND.value,
        },
        # 静态字段名：与 RevokeTransData.host_process_check 一一对应
        write_payload_var="host_process_check",
    )

    # ---- 段 2：组级判定汇聚 F1~F4 + Group决策矩阵 ----
    # 段 2 直接读 trans_data.host_process_check，无需通过 kwargs 传字段名
    sub_pipeline.add_act(
        act_name=_("组级判定 [{ips}]").format(ips=ips_display),
        act_component_code=ResourceGroupJudgeComponent.code,
        kwargs={
            "group_dict": asdict(group),
            "ticket_id": ticket_id,
        },
    )

    # ---- 段 3：元数据精确清理（非 GROUP_RECYCLE 自动 no-op）----
    # 段 3 直接读 trans_data.group_verdict / group_verdict_decision；
    # 本节点不再向 trans_data 写入任何字段，也不再调用 FlowSummary 写入
    # （FlowSummary 预申报已前移至段 2 Judge；清理失败通过 return False 挂起节点）
    sub_pipeline.add_act(
        act_name=_("元数据清理 [{ips}]").format(ips=ips_display),
        act_component_code=ResourceGroupCleanupComponent.code,
        kwargs={
            "bk_biz_id": int(sub_data["bk_biz_id"]),
            "cluster_domains": list(group.cluster_domains),
            # 日志主标识用：Service 内直接 kwargs.get("ips_display") 展示，
            # 与 act_name 保持一致，便于流程节点 <-> 日志关联
            "ips_display": ips_display,
        },
    )

    # ---- 段 4：机器脚本清理（自主基于 trans_data.group_verdict 筛选 F4=yes 的 IP；空则 no-op）----
    sub_pipeline.add_act(
        act_name=_("机器脚本清理 [{ips}]").format(ips=ips_display),
        act_component_code=ResourceGroupMachineClearComponent.code,
        kwargs={},
    )

    return sub_pipeline.build_sub_process(sub_name=_("资源组主机退回 [{ips}]").format(ips=ips_display))
