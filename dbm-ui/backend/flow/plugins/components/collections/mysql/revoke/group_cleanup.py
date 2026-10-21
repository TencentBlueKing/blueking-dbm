# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主机退回资源池 · 清理子流程 bamboo Service / Component。

模块职责：
  - :class:`ResourceGroupCleanupService` · 元数据精确清理（按 evidence · 仅 host 相关）
      * 非 GROUP_RECYCLE 结论直接 no-op 结束
      * GROUP_RECYCLE 结论：
        - 按 evidence.f3_dbm_residue.tuples 清 StorageInstanceTuple
        - 按 evidence.f3_dbm_residue.machine/storages/proxies 清 Machine 元数据
      * 任一清理步失败 -> **节点挂起（return False）**，由 DBA 在 bamboo 页面介入排查并原地重试；
        不做软降级 / 不改判决策，保证清理失败能作为红色告警被及时暴露
      * 本节点不再向 ``trans_data`` 写入任何字段、不再调用 FlowSummary 写入（见 requirements §1/§2）：
        - ``pending_clear_ips`` 已废弃；段 4 自主基于 ``group_verdict`` 筛选 F4=yes 的 IP
        - FlowSummary 写入已前移至段 2 Judge：决策产出瞬间同步追加（语义=决策派发，而非清理完成）
  - :class:`ResourceGroupMachineClearService` · 机器脚本下发（继承自 ClearMachineScriptService）
      * 直接读 ``trans_data.group_verdict`` + ``group_verdict_decision``，自主筛选 F4=yes 的 IP
      * 筛选结果为空（含非 RECYCLE / verdicts 空 / 全部 F4=no） -> 直接 return True 跳过
      * 非空 -> 回填 kwargs["exec_ips"] 后走父类 BkJobService 的 Job 下发 + 轮询逻辑

设计要点：
  - **判据 evidence = 清理清单**：判据里有什么才清什么，不做无差别清理
  - **只清 host 相关元数据**：revoke_flow 的语义是"退回本单申领的机器"，不是"下线集群"。
    Cluster / ClusterEntry 等集群维度元数据的生命周期归属于独立的 destroy_flow；
    在替换类 / 扩容类单据场景下，集群本身还需承载其他机器，绝不能在 revoke 阶段删。
  - **DNS 摘除不在 cleanup 阶段做**：F2.a 已将"DNS 有任何本机记录"作为红线拦下（
    命中则 verdict=KEEP/MANUAL，不会进入 cleanup）；到 cleanup 的机器 DNS 层自己就是干净的
  - **元数据清理直接调 DB 层 API**（不走 bamboo 组件），因为这些是 python 层的同步操作，
    放在同一 Service 内可保证事务性和错误处理一致
  - **机器脚本下发必须走 Job API 异步**，所以拆一个专用组件复用 ClearMachineScriptService
  - **静态字段名**：与 :class:`RevokeTransData` 预声明字段一一对应；SubProcess 隔离保证组间无冲突
"""
import logging
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.models import StorageInstanceTuple
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.mysql.revoke.base.log_utils import group_decision_zh
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.common.exec_clear_machine import ClearMachineScriptService

logger = logging.getLogger("flow")

#: GROUP_RECYCLE 组决策字符串（与 GroupDecision.GROUP_RECYCLE.value 保持一致）
_GROUP_RECYCLE_VALUE: str = "group_recycle"


class ResourceGroupCleanupService(BaseService):
    """组级 · 元数据精确清理 Service。

    kwargs 契约（上层建节点时必须传入）：
      - ``bk_biz_id``         (int, 必填)  业务 id
      - ``cluster_domains``   (list[str], 可选)  本组承载的集群主域名列表（仅用于日志展示，
        表明"本组机器归属哪些集群"；**不参与清理动作**，集群元数据由独立 destroy_flow 管理）
      - ``ips_display``       (str, 可选)  组内 IP 列表字符串（供日志主标识用；
        由 :func:`format_group_ips` 生成，与 act_name 保持一致）

    trans_data 输入（由段 2 :class:`ResourceGroupJudgeService` 写入）：
      - ``group_verdict``            asdict 序列化的 :class:`GroupVerdict` dict
      - ``group_verdict_decision``   :class:`GroupDecision` 的 .value 字符串

    trans_data 输出：
      - **本节点不再向 trans_data 写入任何字段**（``pending_clear_ips`` 已废弃；
        段 4 自主基于 ``group_verdict`` 筛选 F4=yes 的 IP 作为 exec_ips）
      - **本节点不再调用 FlowSummary 写入**（已迁移至段 2 Judge：决策产出瞬间同步追加）

    边界：
      - kwargs 关键字段缺失 -> log error 返回 False
      - group_verdict 缺失 / 非 GROUP_RECYCLE / verdicts 为空 -> 仅日志输出，直接 return True
      - 任一清理步失败 -> 记 ERROR 日志、**返回 False 让节点挂起**；
        由 DBA 在 bamboo 页面排查并原地重试本节点（不做软降级 / 不改判决策）
    """

    def _execute(self, data, parent_data) -> bool:
        """按 group_verdict evidence 精确清理元数据。

        :param data: bamboo 节点数据对象
        :param parent_data: bamboo 父节点数据对象（不使用）
        :return: True 清理完成 / no-op；False 清理过程异常，节点挂起等待 DBA 介入
        """
        kwargs: Dict[str, Any] = data.get_one_of_inputs("kwargs") or {}
        node_name: str = kwargs.get("node_name") or self.__class__.__name__
        bk_biz_id: Optional[int] = kwargs.get("bk_biz_id")
        cluster_domains: List[str] = kwargs.get("cluster_domains") or []
        # 组内 IP 列表字符串：与 act_name 一致，仅用于日志主标识（不参与业务逻辑）
        ips_display: str = kwargs.get("ips_display") or ""

        if not isinstance(bk_biz_id, int):
            self.log_error(_("[{}] kwargs 缺失关键字段 bk_biz_id").format(node_name))
            return False

        trans_data = data.get_one_of_inputs("trans_data")

        # ---- 1. 读组决策（静态字段：SubProcess 隔离保证组间无冲突）----
        gv_dict = getattr(trans_data, "group_verdict", None) if trans_data is not None else None
        decision: str = getattr(trans_data, "group_verdict_decision", "") if trans_data is not None else ""

        if not isinstance(gv_dict, dict) or not gv_dict:
            self.log_error(_("[{}] trans_data.group_verdict 缺失或非 dict，跳过清理").format(node_name))
            return True

        if decision != _GROUP_RECYCLE_VALUE:
            self.log_info(
                _("本组决策={decision_zh}（{decision}），非可清理场景，跳过清理 · IP: {ips}").format(
                    decision_zh=group_decision_zh(decision),
                    decision=decision.upper() if decision else "UNKNOWN",
                    ips=ips_display,
                )
            )
            return True

        # ---- 2. GROUP_RECYCLE：解析 verdicts 收集清理动作输入 ----
        verdicts: List[Dict[str, Any]] = gv_dict.get("verdicts") or []
        if not verdicts:
            self.log_error(_("[{}] group_verdict.verdicts 为空，跳过清理").format(node_name))
            return True

        self.log_info(
            _("开始清理本组 · 单机数={n} 集群数={c} · IP: {ips}").format(n=len(verdicts), c=len(cluster_domains), ips=ips_display)
        )

        # ---- 3. 逐台执行元数据清理（职责纯粹化：本节点不再做任何 trans_data 写入 / FlowSummary 落地） ----
        cleaned_ips: List[str] = []
        try:
            for v in verdicts:
                self._cleanup_one_host(v, node_name=node_name)
                ip_val = (v.get("unit") or {}).get("ip")
                if ip_val:
                    cleaned_ips.append(ip_val)

            # ---- 集群维度元数据清理：不在 revoke_flow 职责范围内 ----
            # revoke_flow 的语义是"退回本单申领的机器"，仅清理 host 相关元数据（Machine / StorageInstanceTuple）。
            # Cluster / ClusterEntry 的生命周期归属独立的 destroy_flow；替换类 / 扩容类单据下集群仍需承载其他机器，
            # 绝不能在此阶段删除集群维度元数据。若发现孤儿 Cluster 需 DBA 检查后走 destroy_flow 处置。

        except Exception as err:
            # 清理失败属于必须人工关注的严重问题：直接让节点挂起（红色），由 DBA 在 bamboo 页面
            # 排查原因（元数据状态 / 下游 API / DB 连接等）后原地重试本节点，而非软降级为 MANUAL。
            # 理由：
            #   1. 清理过程可能出现"元数据删一半"的中间态，必须阻断下游 Job 下发，防止"元数据乱 + 进程被杀"的脏状态
            #   2. return False 让 bamboo 节点红色失败，DBA 能第一时间感知，比隐式改判 MANUAL 更强信号
            #   3. 不写任何 trans_data 字段：节点挂起后下游段 4 不会被执行，无需熔断字段
            self.log_error(_("清理动作失败：{err} · 节点挂起等待 DBA 介入排查并重试 · IP: {ips}").format(err=err, ips=ips_display))
            logger.exception(err)
            return False

        self.log_info(
            _("[清理完成] 已清理机器数={cleaned} · 清理 IP: {cleaned_ips} · IP: {ips}").format(
                cleaned=len(cleaned_ips), cleaned_ips=",".join(cleaned_ips), ips=ips_display
            )
        )
        return True

    def _cleanup_one_host(self, verdict_dict: Dict[str, Any], node_name: str) -> None:
        """清理一台机器的 F3 类残留（StorageInstanceTuple + Machine 元数据）。

        :param verdict_dict: 单机 verdict dict（asdict 序列化的 RevokeVerdict）
        :param node_name: 日志前缀节点名
        :return: None
        边界：
          - 任一清理步失败会 raise 到上层，由上层做组决策改判
          - DNS 摘除：F2.a 已作为"DNS 有任何记录即红线 YES"的关卡；能走到本方法的机器
            意味着 F2.a=NO（DNS 上没有本机记录），故 cleanup 阶段不再做 DNS 摘除
        """
        unit = verdict_dict.get("unit") or {}
        facts = verdict_dict.get("facts") or {}
        ip: str = unit.get("ip") or ""
        bk_host_id: int = int(unit.get("bk_host_id") or 0)
        bk_cloud_id: int = int(unit.get("bk_cloud_id") or 0)

        # ---- F3.c StorageInstanceTuple 清理 ----
        tuples: List[Dict[str, Any]] = ((facts.get("f3_dbm_residue") or {}).get("evidence") or {}).get("tuples") or []
        if tuples:
            tuple_ids: List[int] = [int(t["id"]) for t in tuples if isinstance(t, dict) and "id" in t]
            if tuple_ids:
                deleted, _dels = StorageInstanceTuple.objects.filter(id__in=tuple_ids).delete()
                self.log_info(_("[{}] ip={} 清 StorageInstanceTuple {} 条").format(node_name, ip, deleted))

        # ---- F3.a/d Machine 元数据清理 ----
        f3_ev = (facts.get("f3_dbm_residue") or {}).get("evidence") or {}
        has_machine = bool(f3_ev.get("machine"))
        has_storages = bool(f3_ev.get("storages"))
        has_proxies = bool(f3_ev.get("proxies"))
        if has_machine or has_storages or has_proxies:
            self._clear_machine_meta(bk_host_id=bk_host_id, ip=ip, bk_cloud_id=bk_cloud_id, node_name=node_name)

    def _clear_machine_meta(self, bk_host_id: int, ip: str, bk_cloud_id: int, node_name: str) -> None:
        """清理一台机器的 Machine + 实例元数据。

        直接调用 db_meta.api.machine.clear_info_for_machine，与老实现的 clear_machines 等价。

        :param bk_host_id: 主机 id
        :param ip: 主机 IP（仅日志用）
        :param bk_cloud_id: 云区域
        :param node_name: 日志前缀
        :return: None
        边界：
          - 底层 API 异常 -> raise 到上层
        """
        # 延迟 import 避免与 backend.db_meta.api 的循环 import 风险
        from backend.db_meta import api as db_meta_api

        db_meta_api.machine.clear_info_for_machine(
            machines=[{"ip": ip, "bk_host_id": bk_host_id, "bk_cloud_id": bk_cloud_id}]
        )
        self.log_info(_("[{}] 清 Machine 元数据 ip={} bk_host_id={}").format(node_name, ip, bk_host_id))


class ResourceGroupCleanupComponent(Component):
    """组级 · 元数据精确清理 bamboo 组件。"""

    name = __name__
    code = "resource_group_cleanup"
    bound_service = ResourceGroupCleanupService


class ResourceGroupMachineClearService(ClearMachineScriptService):
    """组级 · 机器脚本清理 Service（继承自 ClearMachineScriptService，支持从 trans_data 动态取 exec_ips）。

    kwargs 契约：
      - 无必填字段；node_name / root_id / node_id 等由 add_act 自动注入

    trans_data 输入（由段 2 :class:`ResourceGroupJudgeService` 写入）：
      - ``group_verdict``            asdict 序列化的 :class:`GroupVerdict` dict
      - ``group_verdict_decision``   :class:`GroupDecision` 的 .value 字符串

    行为（**自主筛选 F4=yes 的 IP**，不再依赖段 3 产出的 ``pending_clear_ips``）：
      - 非 GROUP_RECYCLE 决策 -> 直接 return True 跳过
      - verdicts 为空 / 缺失 -> 直接 return True 跳过（log_error 作异常观测点）
      - 遍历 verdicts 筛选 ``facts.f4_process.state == "yes"`` 的条目组成 ``exec_ips``
      - 筛选结果为空（全部 F4=no，无进程可清）-> 直接 return True 跳过
      - 非空 -> 回填 kwargs["exec_ips"] + kwargs["account_alias"] 后走父类逻辑

    边界：
      - trans_data.group_verdict 缺失 / decision 非 GROUP_RECYCLE / verdicts 空 / 筛选结果空
        -> 均视作 no-op，设置 ``data.outputs.ext_result = True`` 后 return True
      - 父类下发失败 -> 继承父类的 return False 语义
    """

    def _execute(self, data, parent_data) -> bool:
        """从 trans_data.group_verdict 自主筛选 F4=yes 的 IP 作为 exec_ips 后走父类逻辑。

        :param data: bamboo 节点数据
        :param parent_data: 父节点数据
        :return: True 跳过（no-op）或 父类 _execute 结果
        """
        kwargs: Dict[str, Any] = data.get_one_of_inputs("kwargs") or {}
        node_name: str = kwargs.get("node_name") or self.__class__.__name__

        trans_data = data.get_one_of_inputs("trans_data")
        # 静态字段：SubProcess 隔离保证组间无冲突
        gv_dict = getattr(trans_data, "group_verdict", None) if trans_data is not None else None
        decision: str = getattr(trans_data, "group_verdict_decision", "") if trans_data is not None else ""

        # ---- 分支 A：非回收决策（SKIP / KEEP / MANUAL 等） -> no-op ----
        if decision != _GROUP_RECYCLE_VALUE:
            self.log_info(
                _("[{node}] 本组决策={decision}，非回收决策，跳过机器脚本清理（no-op）").format(
                    node=node_name, decision=decision.upper() if decision else "UNKNOWN"
                )
            )
            # 关键契约：父类 BkJobService._schedule 会读 ``data.outputs.ext_result``；
            # 若不写值则默认 None，父类 ``ext_result["result"]`` 会抛 TypeError。
            # 写为 bool 会让父类 ``isinstance(ext_result, bool)`` 分支命中，视作同步组件自动结束调度。
            data.outputs.ext_result = True
            return True

        # ---- 分支 B：判决为 RECYCLE 但 verdicts 空 -> 异常观测点，但 no-op 不阻塞 ----
        verdicts: List[Dict[str, Any]] = (gv_dict or {}).get("verdicts") or [] if isinstance(gv_dict, dict) else []
        if not verdicts:
            self.log_error(
                _("[{node}] group_verdict_decision=GROUP_RECYCLE 但 verdicts 为空，跳过机器脚本清理").format(node=node_name)
            )
            data.outputs.ext_result = True
            return True

        # ---- 分支 C：遍历 verdicts 筛选 F4=yes 的 unit，组装 exec_ips ----
        exec_ips: List[Dict[str, Any]] = []
        for v in verdicts:
            f4_state: str = ((v.get("facts") or {}).get("f4_process") or {}).get("state") or ""
            if f4_state != "yes":
                continue
            unit_dict: Dict[str, Any] = v.get("unit") or {}
            ip_val = unit_dict.get("ip")
            bk_cloud_id_val = unit_dict.get("bk_cloud_id")
            if not ip_val or bk_cloud_id_val is None:
                self.log_error(
                    _("[{node}] verdict.unit 关键字段缺失，跳过本机 F4 清理；unit={unit}").format(node=node_name, unit=unit_dict)
                )
                continue
            exec_ips.append({"ip": ip_val, "bk_cloud_id": bk_cloud_id_val})

        # ---- 分支 D：筛选结果为空（所有机器 F4=no，无进程可清） -> no-op ----
        if not exec_ips:
            self.log_info(_("[{node}] 所有机器 F4=no，无需脚本清理（no-op）").format(node=node_name))
            data.outputs.ext_result = True
            return True

        # ---- 分支 E：有需要清进程的机器 -> 回填 kwargs 后走父类下发逻辑 ----
        kwargs["exec_ips"] = exec_ips
        kwargs.setdefault("account_alias", DBA_ROOT_USER)
        self.log_info(
            _("[{node}] 准备下发机器脚本清理 · 机器数={n} · exec_ips={ips}").format(node=node_name, n=len(exec_ips), ips=exec_ips)
        )
        return super()._execute(data=data, parent_data=parent_data)


class ResourceGroupMachineClearComponent(Component):
    """组级 · 机器脚本清理 bamboo 组件。"""

    name = __name__
    code = "resource_group_machine_clear"
    bound_service = ResourceGroupMachineClearService
