# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBHA Proxy 整机替换类单据 · 候选主机 Extractor。

模块职责：
  - 从 ``MYSQL_PROXY_SWITCH`` 单据的 ticket_data 提取每个 info 对应的 :class:`ResourceGroup` **列表**
  - 本次只申领新 target proxy 一批机器；老 proxy 复用现有 / 不随本次 revoke 退回
  - 机器角色硬编码：``target_proxies[*]`` → role=proxy（:data:`PROXY`）
  - 端口 / 域名从 ``info["cluster_ids"]`` 反查 DBM 元数据得到

分组口径（关键设计点）：
  - 单条 info 内的 N 台新 target_proxy **每台独立成组**（一组 1 unit），而非整组绑定。
    依据：``target_proxies[i]`` 与 ``origin_proxies[i]`` 是**一一对应**的替换关系，flow 内部
    ``tran_ticket_data`` 本来就按索引配对拆分成单台处理；每台 target_proxy 替换一台 origin_proxy
    的生命周期**完全独立**，一台成功一台失败互不干扰——拆成一台一组后组决策更精准，不会被
    "任一台 MANUAL 拖累全组降级"
  - 一台一组后，与 TenDBSingle / Proxy 扩容的分组口径统一

与 Slave 侧 Extractor 的关键差异：
  - **端口口径为 proxy_port**（而非 storage port）：expected_ports 来自 ``ProxyInstance.port``
    去重，与 F3/F4 清理动作对齐（proxy 层按 proxy_port 精确摘路由与清进程）

关键字段契约（revoke 入口 ticket_data 来自父单据 ``details["ticket_data"]``，即
``MysqlProxySwitchParamBuilder`` 产出的结构；``MySQLProxyClusterSwitchFlow.tran_ticket_data``
的运行时拆分仅发生在 flow 内部副本，details 落库仍是复数形式）：
  - ``info["cluster_ids"]``: ``List[int]``，关联集群 ID 列表
  - ``info["target_proxies"]``: ``List[dict]``，本次申请的新 proxy 列表（每项含 ``ip`` / ``bk_host_id`` / ``bk_cloud_id``）
  - ``info["origin_proxies"]``: ``List[dict]``，老 proxy 列表（**本 Extractor 不读取**）

模块边界：
  - ``infos`` / ``bk_biz_id`` / 单条 info 的通用校验下沉至 :class:`HostExtractor`
  - 本模块只校验 ``target_proxies`` 本单据特有字段
  - 严禁读取 ``origin_proxies`` 中的任何机器（老机器不进 revoke 候选）
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
_ERR_PREFIX: str = "[MysqlProxySwitchExtractor]"


class MysqlProxySwitchExtractor(HostExtractor):
    """TenDBHA Proxy 整机替换单据的候选主机 Extractor。

    职责：
      - 为单条 info 内的每台新 target_proxy 产出**一个独立** :class:`ResourceGroup`（组内 1 个 unit，
        role=proxy）；一个 info 的 N 台机器 → N 个 ResourceGroup，由基类 ``extract`` 外层循环
        汇成扁平列表后交给 :class:`MysqlRevokeFlowBase._do_revoke_flow` 做组间并行
      - ``access_layer_proxies`` 保持默认空元组：Proxy 单据候选自身即接入层，F2.d 判据不依赖
        同集群"旁路"的 proxy 探测入口；判定由 host_check 的其他 F 子判据覆盖

    使用方式：
      extractor = MysqlProxySwitchExtractor()
      groups = extractor.extract(ticket_data)  # 展开后每台 proxy 独立一组

    线程安全：是（无实例状态）
    边界：
      - ``target_proxies`` 为空 / 非 list → 抛 :class:`NormalTenDBFlowException`
      - 任一 target proxy 缺 ip / bk_host_id → 抛 :class:`NormalTenDBFlowException`
      - ``cluster_ids`` 关联集群已删除或无任何 ProxyInstance → 抛 :class:`NormalTenDBFlowException`
      - 严禁读取 ``origin_proxies`` 中的任何机器
    """

    #: 日志/异常前缀：供基类统一错误消息使用
    _err_prefix: str = _ERR_PREFIX

    def _extract_one_info(
        self,
        info: Dict[str, Any],
        info_idx: int,
        bk_biz_id: int,
    ) -> List[ResourceGroup]:
        """处理单条 info，为内部每台新 target_proxy 产出独立 :class:`ResourceGroup`。

        :param info: 已校验为 dict 的单条 info（含 ``cluster_ids`` / ``target_proxies``）
        :param info_idx: info 索引
        :param bk_biz_id: 业务 id
        :return: ``List[ResourceGroup]``；长度 = len(target_proxies)，每组恰 1 个 unit
        边界：参见类 docstring
        """
        target_proxies = info.get("target_proxies")
        if not isinstance(target_proxies, list) or not target_proxies:
            raise NormalTenDBFlowException(
                message="{} infos[{}].target_proxies empty or non-list: {!r}".format(
                    _ERR_PREFIX, info_idx, target_proxies
                )
            )
        for proxy_idx, p in enumerate(target_proxies):
            validate_host_dict(
                host=p, err_prefix=_ERR_PREFIX, info_idx=info_idx, field_name="target_proxies[{}]".format(proxy_idx)
            )

        # 反查 DBM 元数据：proxy_port 聚合 + 域名聚合（info 内 N 台机器共享同一组元数据，查一次复用）
        meta: Dict[str, Any] = load_tendbha_cluster_meta(
            cluster_ids=info.get("cluster_ids"), err_prefix=_ERR_PREFIX, info_idx=info_idx
        )
        expected_ports: Tuple[int, ...] = meta["proxy_expected_ports"]
        cluster_domains: Tuple[str, ...] = meta["cluster_domains"]

        # 一台一组：N 台 target_proxies → N 个 ResourceGroup；group_id 用 "info_{i}_host_{j}" 保证全局唯一
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
            for proxy_idx, p in enumerate(target_proxies)
        ]
