# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBHA Proxy 扩容类单据 · 候选主机 Extractor。

模块职责：
  - 从 ``MYSQL_PROXY_ADD`` 单据的 ticket_data 提取每个 info 对应的 :class:`ResourceGroup` **列表**
  - 本次只申领新 proxy 一批机器（纯新增，不涉及任何老机器下架）
  - 机器角色硬编码：``new_proxies[*]`` → role=proxy（:data:`PROXY`）
  - 端口 / 域名从 ``info["cluster_ids"]`` 反查 DBM 元数据得到；扩容场景新机器复用现有 proxy_port

分组口径（关键设计点）：
  - 单条 info 内的 N 台新 proxy **每台独立成组**（一组 1 unit），而非整组绑定。
    依据：Proxy 扩容场景下 N 台新 proxy 之间没有任何生命周期耦合——不像 TenDBHA 部署那样
    一组 inst_num 展开要求整组一起成败；也不像主从迁移那样"新 master + 新 slave"必须成对；
    每台独立判定（F1~F4）、独立清理（A/C/D）、独立回收（E），天然并行且互不干扰。
  - 一台一组后，组决策矩阵的 R1/R2 聚合不再把"任一台 MANUAL 拖累全组降级"，提升回收精度；
    与 TenDBSingle / Proxy 替换的分组口径对齐

与 ``MysqlProxySwitchExtractor`` 的关键差异：
  - 字段名：Add 单据的新 proxy 字段为 ``new_proxies``；Switch 单据为 ``target_proxies``
  - Add 场景没有 ``origin_proxies`` 对比校验（纯扩容，不涉及老机器）
  - 其余端口口径、cluster_meta 反查逻辑完全一致

关键字段契约（revoke 入口 ticket_data 来自父单据 ``details["ticket_data"]``）：
  - ``info["cluster_ids"]``: ``List[int]``
  - ``info["new_proxies"]``: ``List[dict]``，本次申请的新 proxy 列表

模块边界：
  - ``infos`` / ``bk_biz_id`` / 单条 info 的通用校验下沉至 :class:`HostExtractor`
  - 本模块只校验 ``new_proxies`` 本单据特有字段
  - ``cluster_ids`` 关联集群已删除或不存在任何 ProxyInstance → 抛 :class:`NormalTenDBFlowException`
"""
from typing import Any, Dict, List, Tuple

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import ResourceGroup, RevokeUnit
from backend.flow.engine.bamboo.scene.mysql.revoke.base.role_consts import PROXY
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors._cluster_meta import (
    load_tendbha_cluster_meta,
    validate_host_dict,
)
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors.base import HostExtractor

#: 日志/异常前缀：便于在 revoke_flow 顶层兜底日志中快速定位来源
_ERR_PREFIX: str = "[MysqlProxyAddExtractor]"


class MysqlProxyAddExtractor(HostExtractor):
    """TenDBHA Proxy 扩容单据的候选主机 Extractor。

    职责：
      - 为单条 info 内的每台新 proxy 产出**一个独立** :class:`ResourceGroup`（组内 1 个 unit，
        role=proxy）；一个 info 的 N 台机器 → N 个 ResourceGroup，由基类 ``extract`` 外层循环
        汇成扁平列表后交给 :class:`MysqlRevokeFlowBase._do_revoke_flow` 做组间并行
      - 从 ``info["cluster_ids"]`` 反查 DBM 元数据，装配 ``expected_ports``（proxy_port 口径）
        与 ``cluster_domains``
      - ``access_layer_proxies`` 保持默认空元组：Proxy 单据候选自身即接入层，F2.d 判据不依赖
        同集群"旁路"的 proxy 探测入口

    使用方式：
      extractor = MysqlProxyAddExtractor()
      groups = extractor.extract(ticket_data)  # 展开后每台 proxy 独立一组

    线程安全：是（无实例状态）
    边界：
      - ``new_proxies`` 为空 / 非 list / 任一 proxy 缺 ip|bk_host_id → 抛 :class:`NormalTenDBFlowException`
      - ``cluster_ids`` 非法 / 关联集群无 ProxyInstance → 抛 :class:`NormalTenDBFlowException`
    """

    #: 日志/异常前缀：供基类统一错误消息使用
    _err_prefix: str = _ERR_PREFIX

    def _extract_one_info(
        self,
        info: Dict[str, Any],
        info_idx: int,
        bk_biz_id: int,
    ) -> List[ResourceGroup]:
        """处理单条 info，为内部每台新 proxy 产出独立 :class:`ResourceGroup`。

        :param info: 已校验为 dict 的单条 info（含 ``cluster_ids`` / ``new_proxies``）
        :param info_idx: info 索引
        :param bk_biz_id: 业务 id
        :return: ``List[ResourceGroup]``；长度 = len(new_proxies)，每组恰 1 个 unit
        边界：参见类 docstring
        """
        new_proxies = info.get("new_proxies")
        if not isinstance(new_proxies, list) or not new_proxies:
            raise NormalTenDBFlowException(
                message="{} infos[{}].new_proxies empty or non-list: {!r}".format(_ERR_PREFIX, info_idx, new_proxies)
            )
        for proxy_idx, p in enumerate(new_proxies):
            validate_host_dict(
                host=p, err_prefix=_ERR_PREFIX, info_idx=info_idx, field_name="new_proxies[{}]".format(proxy_idx)
            )

        # 反查 DBM 元数据：proxy_port 聚合 + 域名聚合（info 内 N 台机器共享同一组元数据，查一次复用）
        meta: Dict[str, Any] = load_tendbha_cluster_meta(
            cluster_ids=info.get("cluster_ids"), err_prefix=_ERR_PREFIX, info_idx=info_idx
        )
        expected_ports: Tuple[int, ...] = meta["proxy_expected_ports"]
        cluster_domains: Tuple[str, ...] = meta["cluster_domains"]

        # 一台一组：N 台 new_proxies → N 个 ResourceGroup；group_id 用 "info_{i}_host_{j}" 保证全局唯一
        return [
            ResourceGroup(
                group_id="info_{}_host_{}".format(info_idx, proxy_idx),
                units=(
                    RevokeUnit(
                        ip=str(p["ip"]),
                        bk_host_id=int(p["bk_host_id"]),
                        bk_cloud_id=int(p.get("bk_cloud_id", 0)),
                        bk_biz_id=bk_biz_id,
                        role=PROXY,
                        expected_ports=expected_ports,
                        cluster_type=ClusterType.TenDBHA.value,
                    ),
                ),
                cluster_domains=cluster_domains,
                clb_regions=meta["clb_regions"],
            )
            for proxy_idx, p in enumerate(new_proxies)
        ]
