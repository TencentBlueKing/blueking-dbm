# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBHA Slave 添加类单据 · 候选主机 Extractor。

模块职责：
  - 从 ``MYSQL_ADD_SLAVE`` 单据的 ticket_data 提取每个 info 对应的 :class:`ResourceGroup`
  - 本次只申领新 slave 一台机器（纯新增，不涉及任何老机器下架）
  - 机器角色硬编码：``new_slave`` → role=backend_slave（:attr:`InstanceRole.BACKEND_SLAVE`）
  - 端口 / 域名 / 现有 proxy 全部从 ``info["cluster_ids"]`` 反查 DBM 元数据

与 ``MysqlRestoreSlaveExtractor`` 的关键差异：
  - **字段名不同**：Add 单据的新 slave 字段名是 ``new_slave``（dict），而 Restore 单据是 ``bk_new_slave``
  - 页面支持 N 台 slave：``MysqlAddSlaveParamBuilder.format_ticket_data``（含资源池 ``post_callback``）
    已把每台 new_slave 拆成独立 info，到此处每条 info 固定 1 台 ``new_slave``

模块边界：
  - ``infos`` / ``bk_biz_id`` / 单条 info 的通用校验下沉至 :class:`HostExtractor`
  - 本模块只校验本单据特有字段（``new_slave`` / ``cluster_ids``）
  - 校验失败一律抛 :class:`NormalTenDBFlowException`，由上层顶层 try/except 兜底
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
_ERR_PREFIX: str = "[MysqlAddSlaveExtractor]"


class MysqlAddSlaveExtractor(HostExtractor):
    """TenDBHA Slave 添加单据的候选主机 Extractor。

    职责：
      - 为每个 info 产出一个 :class:`ResourceGroup`，组内固定 1 个 unit（新 slave）
      - 从 ``info["cluster_ids"]`` 反查 DBM 元数据装配端口 / 域名 / 现有 proxy

    使用方式：
      extractor = MysqlAddSlaveExtractor()
      groups = extractor.extract(ticket_data)

    线程安全：是（无实例状态）
    边界：
      - ``new_slave`` 缺失或非 dict / 缺 ip|bk_host_id → 抛 :class:`NormalTenDBFlowException`
      - ``cluster_ids`` 对应集群已被删除 → 抛 :class:`NormalTenDBFlowException`
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

        :param info: 已校验为 dict 的单条 info（含 ``new_slave`` / ``cluster_ids``）
        :param info_idx: info 索引
        :param bk_biz_id: 业务 id
        :return: ``[ResourceGroup]``；每条 info 固定产出 1 组（1 台新 slave 一组）
        边界：参见类 docstring
        """
        # 读取新 slave 主机信息（Add 单据字段名是 new_slave，而非 bk_new_slave）
        new_slave = info.get("new_slave")
        validate_host_dict(host=new_slave, err_prefix=_ERR_PREFIX, info_idx=info_idx, field_name="new_slave")

        # 反查 DBM 元数据
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
