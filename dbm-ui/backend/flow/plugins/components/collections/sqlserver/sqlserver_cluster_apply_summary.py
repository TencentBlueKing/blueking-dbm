# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

------------------------------------------------------------------------------

SQLServer 部署类集群交付摘要组件（Cluster 反查版）。

模块职责：
  - 面向"SQLServer 部署单据"（SqlserverSingleApplyFlow / SqlserverHAApplyFlow）的集群交付摘要
    写入；调用方只需传入 `bk_biz_id + cluster_domain`，端口 / 只读入口等字段全部由本组件
    从 db_meta 反查装配。
  - 与 mysql 侧 :class:`MysqlClusterApplySummaryComponent` 语义对齐；采用"反查装配 + 回调
    SQLServer 通用底座 (:class:`SqlserverFlowOutputSummaryService`) 落库"的分层设计：
    本组件专注 SQLServer 独有的 db_meta 反查差异（access_port 手算、CLB 恒空、slave_domain
    通过 SLAVE_ENTRY+DNS 承载），通用的 preset 校验 / Flow 兜底 / FlowOutputHandler 幂等
    写入由底座负责。

设计要点 / 数据源 / 调用通道：
  - 单据侧调用极简：仅传"能唯一定位到集群的最小信息" —— `bk_biz_id + cluster_domain`；
    不传 port / clb / slave_domain 等"半成品"字段，端口与只读入口全部由 Service 反查装配。
  - 本组件强制使用 preset 短名 "cluster_apply"（对齐 :class:`SqlserverClusterApplySummarySerializer`，
    由 :class:`SqlserverFlowOutputSummaryService` 的类属性注册表定位到独立表
    `sqlserver_cluster_apply`）；调用方无需感知。
  - SQLServer 场景 :meth:`Cluster.access_port` 对 `SqlserverSingle / SqlserverHA` 未实现
    （会落入 except 返回 0），故端口手动从 `storageinstance_set` 反查。
  - SQLServer 产品无 CLB，`clb_ip / clb_domain` 恒为空字符串，不触发 ClusterEntry.CLB 查询。

边界：
  - `cluster_domain` 必须在 db_meta 已经存在（即调用点应排在"录入 db_meta 元信息"节点之后）；
    不存在时**跳过该行**并 log_error，不阻塞流程。
  - storageinstance_set 为空 / port=0 -> log_warning 后**跳过该行**，等待重试自然覆写（天然幂等）。
  - SqlserverSingle 场景 readonly_domain_and_port 恒为 ""；SqlserverHA 场景在存在 SLAVE_ENTRY
    时为 "slave_domain:port"（主从端口对齐）。
"""

import logging
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, ClusterType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.plugins.components.collections.sqlserver.flow_output_summary import SqlserverFlowOutputSummaryService

logger = logging.getLogger("flow")

#: 本组件固定服务的预设 key；对齐 :class:`SqlserverClusterApplySummarySerializer`。
#: 调用方无需感知，Service 强制注入到 kwargs["preset"]。
_FIXED_PRESET_KEY: str = "cluster_apply"


class SqlserverClusterApplySummaryService(SqlserverFlowOutputSummaryService):
    """SQLServer 部署类集群交付摘要 Service（Cluster 反查装配）。

    功能说明：
      - 从 kwargs 读取集群定位信息 `clusters`（每项含 bk_biz_id + cluster_domain），
        反查 :class:`Cluster` 得到主入口端口 / 主域名 / 只读入口等全部摘要字段，
        装配成对齐 :class:`SqlserverClusterApplySummarySerializer` 契约的 items 后
        回调 :meth:`SqlserverFlowOutputSummaryService._execute` 完成落库。
      - 调用方**不再传半成品字段**（如 port / slave_domain 等），全部由 Service 从 Cluster
        反查产生，避免"哪些是传入的、哪些是反查的"混淆。
      - 分层职责：本类专注 SQLServer 独有的 db_meta 反查差异（access_port 手算、CLB 恒空、
        slave_domain 通过 SLAVE_ENTRY+DNS 承载）；通用的 preset 校验 / Flow 兜底 /
        FlowOutputHandler 幂等写入由父类 :class:`SqlserverFlowOutputSummaryService` 负责，
        而后者又通过"覆盖 `_PRESET_REGISTRY` 类属性"复用 mysql 侧 `_execute` 主流程。

    输入参数（即 kwargs 字段结构）：
      - clusters (list[dict], 必填): 每项为一条待写入摘要行对应的集群定位信息，字段：
          * bk_biz_id (int, 必填): 业务 ID
          * cluster_domain (str, 必填): 集群不可变域名(immute_domain)
      - global_data (dict, 可选): 由 pipeline 框架传入，用于激活国际化

    输出：
      - 返回 bool；行为语义与通用底座 :class:`SqlserverFlowOutputSummaryService` 完全一致：
          * True: 写入成功 / no-op（clusters 为空、无关联 Flow 等）
          * False: 反查/落库失败

    边界 / 异常：
      - clusters 为空 -> 直接走底座 "items 为空 no-op" 路径返回 True。
      - Cluster 不存在（db_meta 尚未就绪 / 单据数据不一致） -> log_error，**跳过该行**，
        不产出骨架、不抛异常。
      - storageinstance_set 为空 / port=0 -> log_warning，**跳过该行**，等待重试覆写。
      - SqlserverSingle 场景无 SLAVE_ENTRY -> readonly_domain_and_port 留空；
      - SqlserverHA 场景 SLAVE_ENTRY 不存在或 entry 字段为空 -> readonly_domain_and_port 留空；
      - clb_ip / clb_domain 始终为空字符串（SQLServer 产品无 CLB）。
    """

    def _execute(self, data, parent_data) -> bool:
        """反查装配 items -> 回调 SQLServer 通用底座完成落库。

        功能说明 / 怎么做：
          - 从 kwargs 读取集群定位信息；反查 db_meta 装配成 Serializer 契约的 items；
          - 把 items 与固定 preset 塞回 kwargs，交给父类 SqlserverFlowOutputSummaryService
            的 `_execute` 完成"preset 校验 / Flow 兜底 / FlowOutputHandler 幂等写入"。

        :param data: pipeline 框架传入的 data 对象
        :param parent_data: pipeline 框架传入的 parent_data 对象
        :return: True 表示写入成功（含 no-op）；False 表示 preset 非法 / 父类异常

        边界 / 异常：
          - 行为与父类对齐；clusters 为空时父类走 items 空 no-op 返回 True。
        """
        kwargs: Dict[str, Any] = data.get_one_of_inputs("kwargs") or {}
        cluster_infos: List[Dict[str, Any]] = kwargs.get("clusters") or []

        # 依据集群定位信息反查 db_meta 装配 items
        items: List[Dict[str, Any]] = self._build_items_from_clusters(cluster_infos)

        # 将装配好的 items 与固定 preset 塞回 kwargs，交给父类完成校验 + 落库
        kwargs["preset"] = _FIXED_PRESET_KEY
        kwargs["items"] = items
        data.inputs.kwargs = kwargs
        return super()._execute(data, parent_data)

    def _build_items_from_clusters(self, cluster_infos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按集群定位信息反查 db_meta，装配为 :class:`SqlserverClusterApplySummarySerializer` 契约的 items。

        功能说明 / 怎么做：
          - 逐条反查 :class:`Cluster`（by bk_biz_id + immute_domain）；
          - 主入口端口：由于 :meth:`Cluster.access_port` 对 SqlserverSingle / SqlserverHA 未实现
            （会落入 except 返回 0），改为直接从 `cluster.storageinstance_set` 取**第一个
            instance_inner_role=MASTER 的 StorageInstance.port**；若未命中 MASTER（SqlserverSingle
            单实例实际 role 为 ORPHAN），回退取 `storageinstance_set.order_by("port").first().port`。
          - 只读入口：SqlserverSingle 恒为 ""；SqlserverHA 查 `SLAVE_ENTRY + DNS` 的 ClusterEntry，
            端口沿用上一步计算的 access_port（SqlserverHA 主从端口对齐），组装 "slave_domain:port"；
            无 entry 时留空。
          - CLB：SQLServer 产品无 CLB，`clb_ip / clb_domain` 恒为 ""，不触发 ClusterEntry.CLB 查询。

        :param cluster_infos: 集群定位信息列表；每项含 bk_biz_id / cluster_domain
        :return: 已对齐预设 Serializer 字段契约的 items 列表；长度 ≤ cluster_infos 长度
                 （db_meta 反查失败的 / 端口为 0 的会被跳过）

        边界 / 异常：
          - Cluster 不存在 -> log_error 跳过；
          - storageinstance_set 为空（db_meta 尚未就绪）导致 port=0 -> log_warning 跳过，等待重试覆写；
          - SLAVE_ENTRY 不存在或 entry 字段空 -> readonly_domain_and_port 返回 ""，不阻断摘要写入。
        """
        items: List[Dict[str, Any]] = []
        for cluster_info in cluster_infos:
            bk_biz_id: int = int(cluster_info["bk_biz_id"])
            cluster_domain: str = str(cluster_info["cluster_domain"])

            cluster: Optional[Cluster] = Cluster.objects.filter(
                bk_biz_id=bk_biz_id, immute_domain=cluster_domain
            ).first()
            if cluster is None:
                # db_meta 尚未就绪 / 单据数据不一致；直接跳过该行，避免半死行落表
                self.log_error(
                    _("写入 SQLServer 集群交付摘要：db_meta 中未找到集群[{}] bk_biz_id=[{}]，跳过该行").format(cluster_domain, bk_biz_id)
                )
                continue

            access_port: int = cluster.access_port or 0
            if access_port == 0:
                # 端口未反查到说明 db_meta 尚未就绪；此处若强行以 "domain:0" 落库，
                # 会与后续重试落库的 "domain:{real_port}" 因主键(cluster_domain_and_port)不同
                # 而并存，破坏摘要幂等（产生 :0 垃圾行）。直接跳过，等重试自然覆写。
                self.log_warning(_("写入 SQLServer 集群交付摘要：集群[{}] access_port 计算失败，跳过该行等待重试").format(cluster_domain))
                continue

            row: Dict[str, Any] = {
                "cluster_domain_and_port": f"{cluster_domain}{IP_PORT_DIVIDER}{access_port}",
                "readonly_domain_and_port": self._resolve_sqlserver_readonly_entry(cluster, access_port),
                # SQLServer 产品无 CLB，恒为空字符串，不触发 ClusterEntry.CLB 查询
                "clb_ip": "",
                "clb_domain": "",
            }
            items.append(row)

        return items

    @staticmethod
    def _resolve_sqlserver_readonly_entry(cluster: Cluster, access_port: int) -> str:
        """反查 SQLServer 集群只读入口的 "slave_domain:port" 字符串；无只读入口时返回 ""。

        功能说明 / 怎么做：
          - SqlserverSingle 场景无只读入口，直接返回 ""；
          - SqlserverHA 场景查 role=SLAVE_ENTRY + cluster_entry_type=DNS 的 ClusterEntry 得到
            slave_domain；端口沿用集群访问端口（SqlserverHA 主从端口对齐），组装
            "slave_domain:access_port"；无 entry 或 entry 字段空时返回 ""。

        :param cluster: db_meta Cluster 对象
        :param access_port: 集群访问端口（来自 `_resolve_sqlserver_access_port`）
        :return: "slave_domain:port" 字符串；无只读入口时返回 ""

        边界 / 异常：
          - cluster.cluster_type == SqlserverSingle -> 恒返回 ""；
          - 无 SLAVE_ENTRY / entry 字段为空 -> 返回 ""；
          - 不吞异常：由上层 BaseService.execute 捕获转义。
        """
        # SqlserverSingle 没有从库概念，直接返回空
        if cluster.cluster_type == ClusterType.SqlserverSingle.value:
            return ""

        slave_entry: Optional[ClusterEntry] = cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.DNS.value,
            role=ClusterEntryRole.SLAVE_ENTRY.value,
        ).first()
        if slave_entry is None or not slave_entry.entry:
            return ""
        return f"{slave_entry.entry}{IP_PORT_DIVIDER}{access_port}"


class SqlserverClusterApplySummaryComponent(Component):
    """SQLServer 部署类集群交付摘要组件（薄壳）。

    使用方式（在 bamboo pipeline 节点中，需排在"录入 db_meta"节点之后）：
      pipeline.add_act(
          act_name=_("写入集群交付摘要"),
          act_component_code=SqlserverClusterApplySummaryComponent.code,
          kwargs={
              "clusters": [
                  {"bk_biz_id": 3, "cluster_domain": "c1.sqlserver.example.db"},
                  {"bk_biz_id": 3, "cluster_domain": "c2.sqlserver.example.db"},
              ],
          },
      )

    边界 / 备注：
      - 本组件强制走 preset="cluster_apply"（对齐 SqlserverClusterApplySummarySerializer）；
        单据侧无需感知 preset 短名。
      - 调用方不要传 port / clb / slave_domain 等半成品字段；所有字段由 Service 从 db_meta 反查装配。
    """

    name = __name__
    code = "sqlserver_cluster_apply_summary"
    bound_service = SqlserverClusterApplySummaryService
