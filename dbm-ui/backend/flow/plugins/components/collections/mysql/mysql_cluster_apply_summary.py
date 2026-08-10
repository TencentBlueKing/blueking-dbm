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

mysql/spider 部署类集群交付摘要组件（Cluster 反查版）。

模块职责：
  - 面向"部署单据"的集群交付摘要写入；与通用 :class:`MysqlFlowOutputSummaryComponent`
    的区别是：主入口端口 / CLB IP / CLB 域名 / 只读入口等字段在 pipeline 构建时尚未
    完全可知，只有当"录入 db_meta 元信息" / "CLB 创建落库" 等前置节点跑完后，通过
    db_meta 的 Cluster 反查才可得。

设计要点 / 数据源 / 调用通道：
  - 采用"继承 + 薄壳"分层：本模块的 Service 继承自
    :class:`MysqlFlowOutputSummaryService`，`_execute` 只做一件事——用 kwargs
    传入的"集群定位信息"反查 :class:`Cluster` 得到成品 items，然后回调 super()._execute()
    完成落库；preset 校验 / Flow 兜底 / 幂等落库全部沿用通用底座。
  - 单据侧调用极简：只需要传"能唯一定位到集群的最小信息" —— `bk_biz_id +
    cluster_domain`；主入口端口、CLB、只读入口一律由 Service 从 Cluster 及其
    ClusterEntry 关联对象反查装配，**调用方不再拼装任何"半成品"字段**。

边界：
  - `cluster_domain` 必须在 db_meta 已经存在（即调用点应排在"录入 db_meta 元信息"
    以及可选的 "CLB 创建落库" 节点之后）；不存在时**跳过该行**并 log_error，不阻塞流程。
  - 单据侧无需感知 preset：本组件强制使用 preset="cluster_apply"
    （对齐 :class:`ClusterApplySummarySerializer`）。
"""

import logging
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstanceInnerRole
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.plugins.components.collections.mysql.flow_output_summary import MysqlFlowOutputSummaryService

logger = logging.getLogger("flow")

#: 本组件固定服务的预设 key；对齐 flow_output_presets.ClusterApplySummarySerializer。
#: 调用方无需感知，Service 强制注入到 kwargs["preset"]。
_FIXED_PRESET_KEY: str = "cluster_apply"


class MysqlClusterApplySummaryService(MysqlFlowOutputSummaryService):
    """mysql/spider 部署类集群交付摘要 Service（Cluster 反查装配）。

    功能说明：
      - 从 kwargs 读取集群定位信息 `clusters`（每项含 bk_biz_id + cluster_domain），
        反查 :class:`Cluster` 得到主入口端口(`access_port`) / 主域名 / CLB / 只读入口
        等全部摘要字段，装配成对齐 :class:`ClusterApplySummarySerializer` 契约的
        items 后回调 :meth:`MysqlFlowOutputSummaryService._execute` 完成落库。
      - 调用方**不再传半成品字段**（如 port / clb_ip / readonly_domain 等），全部由
        Service 从 Cluster 反查产生，避免"哪些是传入的、哪些是反查的"混淆。

    输入参数（即 kwargs 字段结构）：
      - clusters (list[dict], 必填): 每项为一条待写入摘要行对应的集群定位信息，字段：
          * bk_biz_id (int, 必填): 业务 ID
          * cluster_domain (str, 必填): 集群不可变域名(immute_domain)
      - global_data (dict, 可选): 由 pipeline 框架传入，用于激活国际化

    输出：
      - 返回 bool；行为语义与父类完全一致：
          * True: 写入成功 / no-op（clusters 为空、无关联 Flow 等）
          * False: 反查/父类落库失败

    边界 / 异常：
      - clusters 为空 -> 直接调用父类，走 "items 为空 no-op" 路径返回 True。
      - Cluster 不存在（db_meta 尚未就绪 / 单据数据不一致） -> log_error，**跳过该行**，
        不产出骨架、不抛异常，避免把无效行落到摘要表里。
      - Cluster.access_port 抛异常或返回 0 -> log_warning，端口字段填 0，其余字段照常。
      - CLB ClusterEntry 不存在 -> 视为该集群未启用 CLB，clb_ip / clb_domain 留空。
      - 只读入口 slave ClusterEntry 不存在 -> readonly_domain_and_port 留空。
    """

    def _execute(self, data, parent_data) -> bool:
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
        """按集群定位信息反查 db_meta，装配为 :class:`ClusterApplySummarySerializer` 契约的 items。

        功能说明 / 怎么做：
          - 逐条反查 :class:`Cluster`（by bk_biz_id + immute_domain）；
          - 主入口：`{immute_domain}:{Cluster.access_port}`；
              * `access_port` 已按 cluster_type 自动返回 TenDBSingle 存储端口 /
                TenDBHA proxy 端口 / TenDBCluster spider master 端口；
          - 只读入口：查 role=SLAVE_ENTRY 的 DNS ClusterEntry；端口沿用同一 `access_port`
            对于 TenDBHA 语义并不准确（只读走 mysql_port）——此处对 TenDBHA 单独处理，
            见下方代码；
          - CLB：查 cluster_entry_type=CLB 的 ClusterEntry，取 `detail.clb_ip / clb_domain`。
          - Cluster 不存在的记录直接跳过（不产出骨架），避免摘要表里出现"半死行"。

        :param cluster_infos: 集群定位信息列表；每项含 bk_biz_id / cluster_domain
        :return: 已对齐预设 Serializer 字段契约的 items 列表；长度 ≤ cluster_infos 长度
                 （db_meta 反查失败的会被跳过）

        边界 / 异常：
          - Cluster 不存在 -> log_error 跳过；
          - Cluster.access_port 计算为 0（db_meta 尚未就绪） -> log_warning 后**跳过该行**，
            不产出 "domain:0" 骨架，避免与后续重试落库的正确端口行因主键
            (cluster_domain_and_port) 不同而并存、破坏摘要幂等；
          - ClusterEntry 关联查询无匹配 -> 相应字段留空字符串，符合预设 Serializer 的
            allow_blank 契约。
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
                self.log_error(_("写入集群交付摘要：db_meta 中未找到集群[{}] bk_biz_id=[{}]，跳过该行").format(cluster_domain, bk_biz_id))
                continue

            access_port: int = cluster.access_port or 0
            if access_port == 0:
                # 端口未反查到说明 db_meta 尚未就绪；此处若强行以 "domain:0" 落库，
                # 会与后续重试落库的 "domain:{real_port}" 因主键(cluster_domain_and_port)不同
                # 而并存，破坏摘要幂等（产生 :0 垃圾行）。直接跳过，等重试自然覆写。
                self.log_warning(_("写入集群交付摘要：集群[{}] access_port 计算失败，跳过该行等待重试").format(cluster_domain))
                continue

            row: Dict[str, Any] = {
                "cluster_domain_and_port": f"{cluster_domain}{IP_PORT_DIVIDER}{access_port}",
                "readonly_domain_and_port": self._resolve_readonly_entry(cluster),
                "clb_ip": "",
                "clb_domain": "",
            }

            # CLB 反查：单据可能未开启 CLB，此时 entry 为 None，字段保持空字符串
            clb_entry: Optional[ClusterEntry] = cluster.clusterentry_set.filter(
                cluster_entry_type=ClusterEntryType.CLB.value
            ).first()
            if clb_entry is not None:
                detail: Dict[str, Any] = clb_entry.detail or {}
                row["clb_ip"] = detail.get("clb_ip", "") or ""
                row["clb_domain"] = detail.get("clb_domain", "") or ""

            items.append(row)

        return items

    def _resolve_readonly_entry(self, cluster: Cluster) -> str:
        """反查集群只读入口的"域名:端口"字符串；无只读入口时返回空串。

        功能说明 / 怎么做：
          - 只读入口以 role=SLAVE_ENTRY 的 DNS ClusterEntry 承载；
          - 端口从只读 entry 绑定的实例（storageinstance/proxyinstance）反查得到，
            以覆盖 TenDBHA 只读走 mysql_port、TenDBSingle/TenDBCluster 无只读的差异；
          - 存储实例反查按 ``instance_inner_role=SLAVE`` 精确过滤，避免 SLAVE_ENTRY
            意外多绑或数据脏时取到 MASTER 端口；同时显式 ``order_by("port")``，
            保证多绑定时同一集群多次跑摘要返回稳定的端口，摘要幂等可复现；
          - 若精确过滤未命中（SLAVE_ENTRY 未绑任何 SLAVE 存储实例，属数据脏），
            兜底回退到 entry 关联的任意存储实例，避免完全丢失只读入口展示。

        :param cluster: db_meta Cluster 对象
        :return: `"slave_domain:port"` 字符串；无只读 entry 或端口反查失败时返回 ""

        边界 / 异常：
          - 无 SLAVE_ENTRY -> 返回 ""；
          - SLAVE_ENTRY 存在但未绑定任何实例（数据脏） -> log_warning 后返回 ""；
          - SLAVE_ENTRY 已绑但存储实例中无 SLAVE 角色（数据脏） -> 走兜底取任意实例端口，
            不阻断摘要写入。
        """
        slave_entry: Optional[ClusterEntry] = cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.DNS.value,
            role=ClusterEntryRole.SLAVE_ENTRY.value,
        ).first()
        if slave_entry is None or not slave_entry.entry:
            return ""

        # 从 slave entry 绑定的实例反查端口；优先取 storageinstance（TenDBHA 从库直读 mysql_port）
        # 存储实例按 SLAVE 精确过滤 + 端口升序，保证多绑定时选择稳定且语义正确
        bound_storage = None
        if hasattr(slave_entry, "storageinstance_set"):
            bound_storage = (
                slave_entry.storageinstance_set.filter(
                    instance_inner_role=InstanceInnerRole.SLAVE.value,
                )
                .order_by("port")
                .first()
            )
            # 兜底：SLAVE_ENTRY 未绑 SLAVE 存储实例（数据脏），退化为取任意实例端口
            # 避免因数据异常导致摘要完全丢失只读入口展示
            if bound_storage is None:
                bound_storage = slave_entry.storageinstance_set.order_by("port").first()

        # ProxyInstance 无 instance_inner_role 概念（TenDBHA proxy 是接入层，非存储层），
        # 保持原有取法即可
        bound_proxy = slave_entry.proxyinstance_set.first() if hasattr(slave_entry, "proxyinstance_set") else None
        port: int = 0
        if bound_storage is not None:
            port = int(getattr(bound_storage, "port", 0) or 0)
        elif bound_proxy is not None:
            port = int(getattr(bound_proxy, "port", 0) or 0)

        if port == 0:
            self.log_warning(_("写入集群交付摘要：集群[{}] 只读入口 [{}] 未反查到端口").format(cluster.immute_domain, slave_entry.entry))
            return ""
        return f"{slave_entry.entry}{IP_PORT_DIVIDER}{port}"


class MysqlClusterApplySummaryComponent(Component):
    """mysql/spider 部署类集群交付摘要组件（薄壳）。

    使用方式（在 bamboo pipeline 节点中，需排在"录入 db_meta"及"CLB 创建"节点之后）：
      pipeline.add_act(
          act_name=_("写入集群交付摘要"),
          act_component_code=MysqlClusterApplySummaryComponent.code,
          kwargs={
              "clusters": [
                  {"bk_biz_id": 3, "cluster_domain": "c1.mysql.example.db"},
                  {"bk_biz_id": 3, "cluster_domain": "c2.mysql.example.db"},
              ],
          },
      )

    边界 / 备注：
      - 本组件强制走 preset="cluster_apply"（对齐 ClusterApplySummarySerializer）；
        单据侧无需感知 preset 短名。
      - 若单据完全不需要运行时字段，仍建议改回通用
        :class:`MysqlFlowOutputSummaryComponent` 静态传 items，代码更直白。
    """

    name = __name__
    code = "mysql_cluster_apply_summary"
    bound_service = MysqlClusterApplySummaryService
