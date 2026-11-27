# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBCluster 接入层替换/升降配单据（SPIDER_SWITCH_NODES / SPIDER_CONF_UP_DOWN）· 候选主机 Extractor。

模块职责：
  - 从 ``TENDBCLUSTER_SPIDER_SWITCH_NODES`` / ``TENDBCLUSTER_SPIDER_CONF_UP_DOWN`` 单据的
    ticket_data 提取每个 info 内每台新 spider 机器对应的 :class:`ResourceGroup`
  - 两类单据 ticket_data 同构（CONF_UP_DOWN 的 flow 继承 switch，builder post_callback 同样把
    申请角色键改名为 ``spider_new_ip_list``），共用本 Extractor，差异仅体现在 Flow 子类的
    ``_LOG_PREFIX``
  - 本次只申领新 spider 一批机器（老机器下架走独立的 RECYCLE_OLD_HOST，不进本 revoke 候选）
  - 机器角色统一 role=spider（:data:`role_consts.SPIDER`）；expected_ports 仅含 spider 端口
    （tdbctl 与 spider 同一条实例记录、以 admin_port 落库，无独立实例端口）
  - 端口口径（与 ``TenDBClusterSwitchNodesFlow`` 对齐，见 ``spider_switch_nodes.py`` L210-218）：
      · spider_port = 集群级 spider 端口（同集群唯一，master/slave/mnt 共享，一次取值；
        替换语义下新实例复用同一端口）

分组口径：
  - 单条 info 内的 N 台新 spider **每台独立成组**（一组 1 unit）：替换场景下一对一顶替
    （new_hosts[i] 顶替 old_hosts[i]），N 台新机之间无生命周期耦合；
    与 ``MysqlProxyAddExtractor``（Proxy 扩容"一台一组"）口径对齐

关键字段契约（revoke 入口 ticket_data 来自父单据 ``details["ticket_data"]``）：
  - ``info["cluster_id"]``:        int
  - ``info["spider_new_ip_list"]``: ``List[dict]``，本次申请的新 spider 机器列表
    （RESOURCE_BATCH_APPLY 按申请角色回填后，post_callback 改名为 ``spider_new_ip_list``，
    见 ``tendb_spider_switch_nodes.py`` / ``tendb_spider_conf_up_down.py``）
  - ``info["switch_spider_role"]`` 仅单据语义存在（提单时已校验），revoke 侧不消费

模块边界：
  - ``infos`` / ``bk_biz_id`` / 单条 info 的通用校验下沉至 :class:`HostExtractor`
  - 本模块只校验结构必需字段（``spider_new_ip_list`` / ``cluster_id``）；
    单据语义层校验由提单 serializer 与 flow 执行承担，revoke 侧不重复
  - 严禁读取 ``spider_old_ip_list`` 字段（老机器不进 revoke 候选）
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
_ERR_PREFIX: str = "[SpiderSwitchNodesExtractor]"


class SpiderSwitchNodesExtractor(HostExtractor):
    """TenDBCluster 接入层替换/升降配单据的候选主机 Extractor。

    职责：
      - 为单条 info 内的每台新 spider 产出**一个独立** :class:`ResourceGroup`（组内 1 个 unit）
      - 从 ``info["cluster_id"]`` 反查 DBM 元数据，装配 ``expected_ports``
        （集群级 spider 端口，替换语义下新实例复用同一端口）与 ``cluster_domains`` / ``clb_regions``
      - ``access_layer_proxies`` 装配活集群 ctl_primary（fail-fast）：SPIDER 角色 F2 走
        路径 3 三子判据聚合（DNS + CLB + ctl 路由表），检测替换/升降配流程写入的
        mysql.servers 路由残留；ctl 解析失败直接构建报错（单据失败可重试），
        不做运行期降级——RECYCLE_APPLY_HOST 成功后无法重跑

    使用方式：
      extractor = SpiderSwitchNodesExtractor()
      groups = extractor.extract(ticket_data)

    线程安全：是（无实例状态）
    边界：
      - ``spider_new_ip_list`` 为空 / 非 list / 任一机器缺 ip|bk_host_id → 抛 :class:`NormalTenDBFlowException`
      - 集群无 SPIDER_MASTER 实例（无法推导 spider_port） → 抛 :class:`NormalTenDBFlowException`
      - 单据语义层校验（角色取值等）由提单 serializer 与 flow 执行承担，revoke 侧不重复
    """

    #: 日志/异常前缀：供基类统一错误消息使用
    _err_prefix: str = _ERR_PREFIX

    def _extract_one_info(
        self,
        info: Dict[str, Any],
        info_idx: int,
        bk_biz_id: int,
    ) -> List[ResourceGroup]:
        """处理单条 info，为内部每台新 spider 产出独立 :class:`ResourceGroup`。

        :param info: 已校验为 dict 的单条 info（含 ``cluster_id`` / ``spider_new_ip_list``）
        :param info_idx: info 索引
        :param bk_biz_id: 业务 id
        :return: ``List[ResourceGroup]``；长度 = len(spider_new_ip_list)，每组恰 1 个 unit
        边界：参见类 docstring
        """
        # 读取新 spider 主机信息（严禁读取 spider_old_ip_list 字段：老机器不进候选）
        spider_new_ip_list = info.get("spider_new_ip_list")
        if not isinstance(spider_new_ip_list, list) or not spider_new_ip_list:
            raise NormalTenDBFlowException(
                message="{} infos[{}].spider_new_ip_list empty or non-list: {!r}".format(
                    _ERR_PREFIX, info_idx, spider_new_ip_list
                )
            )
        for host_idx, host in enumerate(spider_new_ip_list):
            validate_host_dict(
                host=host,
                err_prefix=_ERR_PREFIX,
                info_idx=info_idx,
                field_name="spider_new_ip_list[{}]".format(host_idx),
            )

        # 反查集群元数据
        meta: Dict[str, Any] = load_tendbcluster_meta(
            cluster_id=info.get("cluster_id"), err_prefix=_ERR_PREFIX, info_idx=info_idx
        )
        # 新机监听端口：本集群 spider 端口（新实例复用集群端口）
        expected_ports: Tuple[int, ...] = (meta["spider_port"],)

        # 装配 ctl_primary 探测入口（fail-fast）：SPIDER 角色 F2 路径 3 聚合追加 ctl 路由子检查
        # （替换/升降配流程写入的 mysql.servers 路由残留检测）；
        # 解析失败直接抛 NormalTenDBFlowException → 顶层 revoke_flow 兜底 → 单据失败可重试
        ctl_primary = get_ctl_primary(cluster=meta["cluster"], err_prefix=_ERR_PREFIX, info_idx=info_idx)

        # 一台一组：N 台新 spider → N 个 ResourceGroup；group_id 用 "info_{i}_host_{j}" 保证全局唯一
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
            for host_idx, host in enumerate(spider_new_ip_list)
        ]
