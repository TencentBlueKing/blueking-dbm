# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBHA 主从迁移类单据 · 候选主机 Extractor。

模块职责：
  - 从 ``MYSQL_MIGRATE_CLUSTER`` 单据的 ticket_data 提取每个 info 对应的 :class:`ResourceGroup`
  - 本次只申领新 master + 新 slave 两台机器（proxy 复用现有，不随本次 revoke 退回）
  - 机器角色硬编码：
      · ``bk_new_master`` → role=backend_master（:attr:`InstanceRole.BACKEND_MASTER`）
      · ``bk_new_slave``  → role=backend_slave  （:attr:`InstanceRole.BACKEND_SLAVE`）
  - 端口 / 域名 / 现有 proxy 全部从 ``info["cluster_ids"]`` 反查 DBM 元数据（而非 ticket_data 自带）

与 Slave 侧 Extractor 的关键差异：
  - 本单组内固定 2 台机器（新 master + 新 slave），而重建 / 添加 slave 单据只有 1 台
  - access_layer_proxies 装的是**现有 proxy 老机器**（不在本 revoke 组内），F2.c/F2.d 判据依赖
    ``host_check._filter_alive_access_layer`` 的 R3 跨组兜底（跨组 proxy 默认视为活），
    继续走 proxyrpc 实查 backends 表来确认迁移是否已完成接入层切换

设计参考：
  - ``backend/ticket/builders/mysql/mysql_migrate_cluster.py`` 的 ticket_data schema
  - ``backend/flow/engine/bamboo/scene/mysql/revoke/extractors/_cluster_meta.py`` 的 Cluster 反查工具

模块边界：
  - ``infos`` / ``bk_biz_id`` / 单条 info 的通用校验下沉至 :class:`HostExtractor`
  - 本模块只校验本单据特有字段（``bk_new_master`` / ``bk_new_slave`` / ``cluster_ids``）
  - 校验失败一律抛 :class:`NormalTenDBFlowException`，由上层 revoke_flow 顶层 try/except 兜底
  - 严禁读取 ``old_master_ip`` / ``old_slave_ip`` / ``old_nodes`` 字段（老机器不进 revoke 候选）
"""
from typing import Any, Dict, List, Tuple

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import ResourceGroup, RevokeUnit
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors._cluster_meta import (
    load_tendbha_cluster_meta,
    validate_host_dict,
)
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors.base import HostExtractor

#: 日志/异常前缀：便于在 revoke_flow 顶层兜底日志中快速定位来源
_ERR_PREFIX: str = "[MysqlMigrateClusterExtractor]"


class MysqlMigrateClusterExtractor(HostExtractor):
    """TenDBHA 主从迁移单据的候选主机 Extractor。

    职责：
      - 为每个 info 产出一个 :class:`ResourceGroup`，组内固定 2 个 unit
        （新 master = backend_master、新 slave = backend_slave）
      - 从 ``info["cluster_ids"]`` 反查 DBM 元数据，装配：
          · ``RevokeUnit.expected_ports``       ← 关联集群全部 ``StorageInstance.port`` 去重
            （新 master / 新 slave 共享同一组端口，与 TenDBHA"同集群主从同端口"约束对齐）
          · ``ResourceGroup.cluster_domains``   ← ``Cluster.immute_domain`` 去重
          · ``ResourceGroup.access_layer_proxies`` ← 现有 RUNNING ``ProxyInstance`` 的 admin_port
            （跨组 R3 兜底，F2.d 走 proxyrpc 实查 backends 判定迁移是否完成接入层切换）

    使用方式：
      extractor = MysqlMigrateClusterExtractor()
      groups = extractor.extract(ticket_data)

    线程安全：是（无实例状态）
    边界：
      - ``bk_new_master`` / ``bk_new_slave`` 缺失或缺 ip / bk_host_id → 抛 :class:`NormalTenDBFlowException`
      - ``cluster_ids`` 非法 / 关联集群已删 → 抛 :class:`NormalTenDBFlowException`（显式失败）
      - 严禁读取 ``old_master_ip`` / ``old_slave_ip`` / ``old_nodes`` 字段
    """

    #: 日志/异常前缀：供基类统一错误消息使用
    _err_prefix: str = _ERR_PREFIX

    def _extract_one_info(
        self,
        info: Dict[str, Any],
        info_idx: int,
        bk_biz_id: int,
    ) -> List[ResourceGroup]:
        """处理单条 info，产出 :class:`ResourceGroup` 单元素列表。

        注意：本单据的新 master + 新 slave 必须成对绑定（主从依赖关系），
        因此一个 info 固定产出 1 组、组内 2 unit——与 proxy_add / proxy_switch 的"一台一组"口径有本质差异。

        :param info: 已校验为 dict 的单条 info（含 ``bk_new_master`` / ``bk_new_slave`` / ``cluster_ids``）
        :param info_idx: info 索引
        :param bk_biz_id: 业务 id
        :return: ``[ResourceGroup]``；每条 info 固定产出 1 组、组内 2 unit（主 + 从）
        边界：参见类 docstring
        """
        # 读取新 master / 新 slave 主机信息（严禁读取 old_* 字段）
        new_master = info.get("bk_new_master")
        new_slave = info.get("bk_new_slave")
        validate_host_dict(host=new_master, err_prefix=_ERR_PREFIX, info_idx=info_idx, field_name="bk_new_master")
        validate_host_dict(host=new_slave, err_prefix=_ERR_PREFIX, info_idx=info_idx, field_name="bk_new_slave")

        # 反查 DBM 元数据：端口 / 域名 / 现有 proxy
        meta: Dict[str, Any] = load_tendbha_cluster_meta(
            cluster_ids=info.get("cluster_ids"), err_prefix=_ERR_PREFIX, info_idx=info_idx
        )
        expected_ports: Tuple[int, ...] = meta["storage_expected_ports"]

        # 组内 units：新 master / 新 slave 共享 bk_biz_id / expected_ports / cluster_type，仅主机 + role 不同
        units: Tuple[RevokeUnit, ...] = tuple(
            RevokeUnit(
                ip=str(host["ip"]),
                bk_host_id=int(host["bk_host_id"]),
                bk_cloud_id=int(host.get("bk_cloud_id", 0)),
                bk_biz_id=bk_biz_id,
                role=role,
                expected_ports=expected_ports,
                cluster_type=ClusterType.TenDBHA.value,
            )
            for host, role in (
                (new_master, InstanceRole.BACKEND_MASTER.value),
                (new_slave, InstanceRole.BACKEND_SLAVE.value),
            )
        )

        return [
            ResourceGroup(
                group_id="info_{}".format(info_idx),
                units=units,
                cluster_domains=meta["cluster_domains"],
                clb_regions=meta["clb_regions"],
                access_layer_proxies=meta["access_layer_proxies"],
            )
        ]
