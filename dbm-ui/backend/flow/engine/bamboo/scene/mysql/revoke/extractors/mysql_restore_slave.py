# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBHA Slave 新机重建类单据 · 候选主机 Extractor。

模块职责：
  - 从 ``MYSQL_RESTORE_SLAVE`` 单据的 ticket_data 提取每个 info 对应的 :class:`ResourceGroup`
  - 本次只申领新 slave 一台机器（master / proxy 全部复用现有，不随本次 revoke 退回）
  - 机器角色硬编码:``bk_new_slave`` → role=backend_slave（:attr:`InstanceRole.BACKEND_SLAVE`）
  - 端口 / 域名 / 现有 proxy 全部从 ``info["cluster_ids"]`` 反查 DBM 元数据（而非 ticket_data 自带）

与 ``MysqlMigrateClusterExtractor`` 的关键差异：
  - Slave 重建单据的 info 只有 1 台新机（新 slave），不像迁移单据 2 台（新 master + 新 slave）；
    因此每组产出 1 个 unit，而非 2 个
  - 端口 / proxy 聚合口径与迁移单据完全一致：复用 :mod:`_cluster_meta.load_tendbha_cluster_meta`

设计参考：
  - ``backend/ticket/builders/mysql/mysql_restore_slave.py`` 的 ticket_data schema
    （``MysqlRestoreSlaveParamBuilder.format_ticket_data`` 后 info 含
    ``cluster_ids`` / ``bk_new_slave`` / ``new_slave_ip`` / ``bk_old_slave`` / ``old_slave_ip``；
    Extractor 只读取 ``cluster_ids`` + ``bk_new_slave``，老机器一律不进候选）

模块边界：
  - ``infos`` / ``bk_biz_id`` / 单条 info 的通用校验下沉至 :class:`HostExtractor`
  - 本模块只校验本单据特有字段（``bk_new_slave`` / ``cluster_ids``）
  - 任何校验失败一律抛 :class:`NormalTenDBFlowException`，由上层 ``revoke_flow`` 顶层 try/except 兜底
  - 严禁读取 ``bk_old_slave`` / ``old_slave_ip`` / ``old_nodes`` 字段（老机器不进 revoke 候选）
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
_ERR_PREFIX: str = "[MysqlRestoreSlaveExtractor]"


class MysqlRestoreSlaveExtractor(HostExtractor):
    """TenDBHA Slave 新机重建单据的候选主机 Extractor。

    职责：
      - 为每个 info 产出一个 :class:`ResourceGroup`，组内固定 1 个 unit（新 slave）
      - 从 ``info["cluster_ids"]`` 反查 DBM 元数据，装配：
          · ``RevokeUnit.expected_ports``       ← 关联集群在 DBM 元数据登记的全部 StorageInstance.port
          · ``ResourceGroup.cluster_domains``   ← Cluster.immute_domain 去重
          · ``ResourceGroup.access_layer_proxies`` ← 现有 RUNNING ProxyInstance 的 admin_port
            （跨组 R3 兜底，F2.d 走 proxyrpc 实查 backends 判定）

    使用方式：
      extractor = MysqlRestoreSlaveExtractor()
      groups = extractor.extract(ticket_data)

    线程安全：是（无实例状态）
    边界：
      - ``bk_new_slave`` 缺失或缺 ip / bk_host_id → 抛 :class:`NormalTenDBFlowException`
      - ``cluster_ids`` 非法 / 关联集群已删 → 抛 :class:`NormalTenDBFlowException`
      - 严禁读取 ``bk_old_slave`` / ``old_slave_ip`` / ``old_nodes`` 字段
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

        :param info: 已校验为 dict 的单条 info（含 ``bk_new_slave`` / ``cluster_ids``）
        :param info_idx: info 索引
        :param bk_biz_id: 业务 id
        :return: ``[ResourceGroup]``；每条 info 固定产出 1 组（1 台新 slave 一组）
        边界：参见类 docstring
        """
        # 读取新 slave 主机信息（严禁读取 bk_old_slave / old_slave_ip 字段）
        new_slave = info.get("bk_new_slave")
        validate_host_dict(host=new_slave, err_prefix=_ERR_PREFIX, info_idx=info_idx, field_name="bk_new_slave")

        # 反查 DBM 元数据：端口 / 域名 / 现有 proxy
        meta: Dict[str, Any] = load_tendbha_cluster_meta(
            cluster_ids=info.get("cluster_ids"), err_prefix=_ERR_PREFIX, info_idx=info_idx
        )
        expected_ports: Tuple[int, ...] = meta["storage_expected_ports"]

        unit = RevokeUnit(
            ip=str(new_slave["ip"]),
            bk_host_id=int(new_slave["bk_host_id"]),
            bk_cloud_id=int(new_slave.get("bk_cloud_id", 0)),
            bk_biz_id=bk_biz_id,
            role=InstanceRole.BACKEND_SLAVE.value,
            expected_ports=expected_ports,
            cluster_type=ClusterType.TenDBHA.value,
        )
        return [
            ResourceGroup(
                group_id="info_{}".format(info_idx),
                units=(unit,),
                cluster_domains=meta["cluster_domains"],
                clb_regions=meta["clb_regions"],
                access_layer_proxies=meta["access_layer_proxies"],
            )
        ]
