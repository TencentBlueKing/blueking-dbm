# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBCluster 只读接入层部署单据（SPIDER_SLAVE_APPLY）· 候选主机 Extractor。

模块职责：
  - 从 ``TENDBCLUSTER_SPIDER_SLAVE_APPLY`` 单据的 ticket_data 提取每个 info 内每台新
    spider_slave（只读接入层）机器对应的 :class:`ResourceGroup`
  - 本次只申领新 spider_slave 一批机器（纯新增，不涉及任何老机器下架）
  - 机器角色硬编码：新机 → role=spider（:data:`role_consts.SPIDER`；spider 全系统一角色，
    差异由 expected_ports 表达），
    **不安装 ctl**，``expected_ports=(spider_port,)`` 仅 spider 端口
  - 端口口径（与 ``add_spider_slaves_sub_flow`` 对齐，见 ``common_sub_flow.py`` L240-257）：
    同集群 spider 端口唯一（master/slave/mnt 共享），直接取 ``meta["spider_port"]``
    （flow 侧 db_meta 写入使用 ``cluster.proxyinstance_set.first().port``，语义等价）
  - ``cluster_domains`` 仅填集群主域名 ``immute_domain``（集群标识）；``slave_domain``
    是同一集群的只读入口域名，不追加——追加会使清理日志"集群数"把同一集群重复计数

分组口径：
  - 单条 info 内的 N 台新 spider_slave **每台独立成组**（一组 1 unit）：只读接入层节点之间
    无任何生命周期耦合；与 ``MysqlProxyAddExtractor``（Proxy 扩容"一台一组"）口径对齐

关键字段契约（revoke 入口 ticket_data 来自父单据 ``details["ticket_data"]``）：
  - ``info["cluster_id"]``:          int
  - ``info["slave_domain"]``:        str（只读入口域名）
  - ``info["spider_slave_ip_list"]``: ``List[dict]``，本次申请的新 spider_slave 机器列表
    （RESOURCE_BATCH_APPLY 按 group_mark ``"{index}_spider_slave_ip_list"`` 回填，post_callback
    仅改 resource_spec 键名、不改机器字段名，见 ``tendb_spider_slave_apply.py``）

模块边界：
  - ``infos`` / ``bk_biz_id`` / 单条 info 的通用校验下沉至 :class:`HostExtractor`
  - 本模块只校验本单据特有字段（``spider_slave_ip_list`` / ``cluster_id``）
  - 校验失败一律抛 :class:`NormalTenDBFlowException`，由上层 ``revoke_flow`` 顶层 try/except 兜底
"""
from typing import Any, Dict, List, Tuple

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import ResourceGroup, RevokeUnit
from backend.flow.engine.bamboo.scene.mysql.revoke.base.role_consts import SPIDER
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors._cluster_meta import validate_host_dict
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors.base import HostExtractor
from backend.flow.engine.bamboo.scene.spider.revoke.extractors._spider_cluster_meta import (
    get_ctl_primary,
    load_tendbcluster_meta,
)

#: 日志/异常前缀：便于在 revoke_flow 顶层兜底日志中快速定位来源
_ERR_PREFIX: str = "[SpiderSlaveApplyExtractor]"


class SpiderSlaveApplyExtractor(HostExtractor):
    """TenDBCluster 只读接入层部署单据的候选主机 Extractor。

    职责：
      - 为单条 info 内的每台新 spider_slave 产出**一个独立** :class:`ResourceGroup`
        （组内 1 个 unit，role=spider）
      - 从 ``info["cluster_id"]`` 反查 DBM 元数据，装配 ``expected_ports``
        （集群级 spider 端口，master/slave/mnt 共享，由 spider_master 元数据推导）
      - ``access_layer_proxies`` 装配活集群 ctl_primary（fail-fast）：spider_slave 走 F2
        路径 3 三子判据聚合（DNS + CLB + ctl 路由表），检测部署流程写入的
        mysql.servers 路由残留；ctl 解析失败直接构建报错（单据失败可重试），
        不做运行期降级——RECYCLE_APPLY_HOST 成功后无法重跑

    使用方式：
      extractor = SpiderSlaveApplyExtractor()
      groups = extractor.extract(ticket_data)

    线程安全：是（无实例状态）
    边界：
      - ``spider_slave_ip_list`` 为空 / 非 list / 任一机器缺 ip|bk_host_id → 抛 :class:`NormalTenDBFlowException`
      - 集群无 spider_master 存量端口可推导（无法得出集群级 spider 端口） → 抛
        :class:`NormalTenDBFlowException`
    """

    #: 日志/异常前缀：供基类统一错误消息使用
    _err_prefix: str = _ERR_PREFIX

    def _extract_one_info(
        self,
        info: Dict[str, Any],
        info_idx: int,
        bk_biz_id: int,
    ) -> List[ResourceGroup]:
        """处理单条 info，为内部每台新 spider_slave 产出独立 :class:`ResourceGroup`。

        :param info: 已校验为 dict 的单条 info（含 ``cluster_id`` / ``slave_domain`` / ``spider_slave_ip_list``）
        :param info_idx: info 索引
        :param bk_biz_id: 业务 id
        :return: ``List[ResourceGroup]``；长度 = len(spider_slave_ip_list)，每组恰 1 个 unit
        边界：参见类 docstring
        """
        spider_slave_ip_list = info.get("spider_slave_ip_list")
        if not isinstance(spider_slave_ip_list, list) or not spider_slave_ip_list:
            raise NormalTenDBFlowException(
                message="{} infos[{}].spider_slave_ip_list empty or non-list: {!r}".format(
                    _ERR_PREFIX, info_idx, spider_slave_ip_list
                )
            )
        for host_idx, host in enumerate(spider_slave_ip_list):
            validate_host_dict(
                host=host,
                err_prefix=_ERR_PREFIX,
                info_idx=info_idx,
                field_name="spider_slave_ip_list[{}]".format(host_idx),
            )

        # 反查集群元数据
        meta: Dict[str, Any] = load_tendbcluster_meta(
            cluster_id=info.get("cluster_id"), err_prefix=_ERR_PREFIX, info_idx=info_idx
        )
        # 新机监听端口：本集群 spider 端口
        expected_ports: Tuple[int, ...] = (meta["spider_port"],)

        # 装配 ctl_primary 探测入口（fail-fast）：SPIDER 角色 F2 路径 3 聚合追加 ctl 路由子检查
        # （部署流程写入的 mysql.servers 路由残留检测）；
        # 解析失败直接抛 NormalTenDBFlowException → 顶层 revoke_flow 兜底 → 单据失败可重试
        ctl_primary = get_ctl_primary(cluster=meta["cluster"], err_prefix=_ERR_PREFIX, info_idx=info_idx)

        # 一台一组：N 台新 spider_slave → N 个 ResourceGroup；group_id 用 "info_{i}_host_{j}" 保证全局唯一
        return [
            ResourceGroup(
                group_id="info_{}_host_{}".format(info_idx, host_idx),
                units=(
                    RevokeUnit(
                        ip=str(host["ip"]),
                        bk_host_id=int(host["bk_host_id"]),
                        bk_cloud_id=int(host.get("bk_cloud_id", 0)),
                        bk_biz_id=bk_biz_id,
                        role=SPIDER,
                        expected_ports=expected_ports,
                        cluster_type=ClusterType.TenDBCluster.value,
                    ),
                ),
                cluster_domains=meta["cluster_domains"],
                clb_regions=meta["clb_regions"],
                access_layer_proxies=(ctl_primary,),
            )
            for host_idx, host in enumerate(spider_slave_ip_list)
        ]
