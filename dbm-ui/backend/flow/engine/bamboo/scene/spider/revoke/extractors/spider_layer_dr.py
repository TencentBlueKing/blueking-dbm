# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBCluster 接入层灾难重建单据（SPIDER_LAYER_DR）· 候选主机 Extractor。

模块职责：
  - 从 ``TENDBCLUSTER_SPIDER_LAYER_DR`` 单据的 ticket_data 提取每个 info 内每台新 spider 机器
    对应的 :class:`ResourceGroup`
  - 本次只申领新接入层机器（灾难重建：被替换的旧接入层机器不进本 revoke 候选，
    其回收由集群下架 / 旧机回收单据承担）
  - 机器角色统一 role=spider（:data:`role_consts.SPIDER`）；expected_ports 仅含 spider 端口
    （tdbctl 与 spider 同一条实例记录、以 admin_port 落库，无独立实例端口）
  - 端口口径（与 ``TenDBClusterSpiderLayerDisasterRecoverFlow`` 对齐）：
      · ``info["spider_port"]`` 可选覆盖；缺省取集群级 ``meta["spider_port"]``
        （同集群唯一，master/slave/mnt 共享）；
        从元数据取值不受实例运行状态影响（DR 场景 masters 全灭亦可推导）

分组口径：
  - 单条 info 内的新 master / 新 slave 机器**每台独立成组**（一组 1 unit）：
    灾难重建场景下各新机独立判定（F1~F4）、独立清理、独立回收；
    与 ``MysqlProxyAddExtractor``（Proxy 扩容"一台一组"）口径对齐

关键字段契约（revoke 入口 ticket_data 来自父单据 ``details["ticket_data"]``）：
  - ``info["cluster_id"]``:               int
  - ``info["spider_master_new_ip_list"]``: ``List[dict]``，重建的 spider_master 机器（可为空）
  - ``info["spider_slave_new_ip_list"]``:  ``List[dict]``，重建的 spider_slave 机器（可为空）
  - ``info["spider_port"]``: 可选 spider 端口覆盖
  - ``info["ctl_port"]``:  可选 tdbctl 端口覆盖（与 DR flow 的
    :func:`resolve_spider_ctl_ports` 口径一致：显式 ctl_port 优先 → spider_port + 1000
    → 元数据 spider_master 的 admin_port 推导）
  - （RESOURCE_BATCH_APPLY 按 ``spider_master_new_ip_list`` / ``spider_slave_new_ip_list``
    角色 key 回填，post_callback 不改机器字段名）

模块边界：
  - ``infos`` / ``bk_biz_id`` / 单条 info 的通用校验下沉至 :class:`HostExtractor`
  - 本模块只校验本单据特有字段
  - 严禁读取 ``spider_master_old_ip_list`` / ``spider_slave_old_ip_list`` 字段（老机器不进候选）
  - 校验失败一律抛 :class:`NormalTenDBFlowException`，由上层 ``revoke_flow`` 顶层 try/except 兜底
"""
from typing import Any, Dict, List, Tuple

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import AccessLayerInstance, ResourceGroup, RevokeUnit
from backend.flow.engine.bamboo.scene.mysql.revoke.base.role_consts import SPIDER
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors._cluster_meta import validate_host_dict
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors.base import HostExtractor
from backend.flow.engine.bamboo.scene.spider.revoke.extractors._spider_cluster_meta import (
    get_ctl_primary,
    load_tendbcluster_meta,
)
from backend.flow.utils.spider.spider_disaster_recover import resolve_spider_ctl_ports

#: 日志/异常前缀：便于在 revoke_flow 顶层兜底日志中快速定位来源
_ERR_PREFIX: str = "[SpiderLayerDisasterRecoverExtractor]"


class SpiderLayerDisasterRecoverExtractor(HostExtractor):
    """TenDBCluster 接入层灾难重建单据的候选主机 Extractor。

    职责：
      - 为单条 info 内的每台新 spider（master / slave 段）产出**一个独立** :class:`ResourceGroup`
      - 端口一行直推：``info["spider_port"]`` 可覆盖，缺省取集群级 ``spider_port``
        （同集群唯一）；从元数据取值不受实例运行状态影响（DR 场景 masters 全灭亦可推导）
      - ``access_layer_proxies`` 装配 ctl_primary 探测入口（SPIDER 角色 F2 路径 3 三子判据
        聚合：DNS + CLB + ctl 路由表），来源按重建范围分流（**确定性来源 = 单据自身**）：
          * master 段重建（spider_master_new_ip_list 非空）：存量中控随灾难全灭，
            元数据反查必然失败，不做反查；``spider_master_new_ip_list[0]`` 即 DR flow
            约定的新主中控（primary_ctl_ip），ctl_port 与 DR flow 对齐走
            :func:`resolve_spider_ctl_ports`（显式 ctl_port 优先 → spider_port + 1000
            → 元数据 spider_master 的 admin_port 推导，不写死 +1000）。
            该机器本身是本单 revoke 候选，判据层存活预判天然覆盖：
            新 ctl 进程活 → 连新 ctl 查路由残留；进程死 → 证伪短路 NO → 正常回收
          * 仅 slave 段重建：集群存量 spider master 存活，反查元数据 ctl_primary
            （fail-fast：反查失败直接构建报错，单据失败可重试）

    使用方式：
      extractor = SpiderLayerDisasterRecoverExtractor()
      groups = extractor.extract(ticket_data)

    线程安全：是（无实例状态）
    边界：
      - master / slave 两个新机列表**同时为空** → 抛 :class:`NormalTenDBFlowException`
        （单据语义至少重建一侧，全空属非法 ticket_data）
      - 任一新机 dict 缺 ip|bk_host_id → 抛 :class:`NormalTenDBFlowException`
      - 端口推导失败（集群无 SPIDER_MASTER 元数据，判空已在 meta 统一收敛） → 抛
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
        """处理单条 info，为新 master / 新 slave 段机器各产出独立 :class:`ResourceGroup`。

        :param info: 已校验为 dict 的单条 info
        :param info_idx: info 索引
        :param bk_biz_id: 业务 id
        :return: ``List[ResourceGroup]``；长度 = len(master_new) + len(slave_new)，每组恰 1 个 unit
        边界：参见类 docstring
        """
        # 读取新接入层机器信息（严禁读取 *_old_ip_list 字段：老机器不进候选）
        master_new = info.get("spider_master_new_ip_list") or []
        slave_new = info.get("spider_slave_new_ip_list") or []
        if not (isinstance(master_new, list) and isinstance(slave_new, list)):
            raise NormalTenDBFlowException(
                message="{} infos[{}].spider_master_new_ip_list/spider_slave_new_ip_list not list: {!r}/{!r}".format(
                    _ERR_PREFIX, info_idx, master_new, slave_new
                )
            )
        if not master_new and not slave_new:
            raise NormalTenDBFlowException(
                message="{} infos[{}] both spider_master_new_ip_list and spider_slave_new_ip_list empty".format(
                    _ERR_PREFIX, info_idx
                )
            )
        for host_idx, host in enumerate(master_new):
            validate_host_dict(
                host=host,
                err_prefix=_ERR_PREFIX,
                info_idx=info_idx,
                field_name="spider_master_new_ip_list[{}]".format(host_idx),
            )
        for host_idx, host in enumerate(slave_new):
            validate_host_dict(
                host=host,
                err_prefix=_ERR_PREFIX,
                info_idx=info_idx,
                field_name="spider_slave_new_ip_list[{}]".format(host_idx),
            )

        # 反查集群元数据
        meta: Dict[str, Any] = load_tendbcluster_meta(
            cluster_id=info.get("cluster_id"), err_prefix=_ERR_PREFIX, info_idx=info_idx
        )
        # 新机监听端口：本集群 spider 端口，可由 info["spider_port"] 覆盖
        spider_port: int = int(info.get("spider_port") or meta["spider_port"])
        expected_ports: Tuple[int, ...] = (spider_port,)

        # ---- 装配 ctl_primary 探测入口（确定性来源 = 单据自身，不反查集群元数据）----
        # master 段重建：存量中控随灾难全灭，cluster.tendbcluster_ctl_primary_address()
        # 反查（含 DRS 实连验证）必然失败。DR flow 约定 spider_master_new_ip_list[0] 即
        # 新主中控（primary_ctl_ip，见 spider_layer_disaster_recover_flow.py），ctl_port
        # 与 DR flow 对齐走 resolve_spider_ctl_ports（显式 ctl_port 优先 →
        # spider_port + 1000 → 元数据 spider_master 的 admin_port 推导），不写死 +1000；
        # 端口推导只读元数据、不依赖实例存活（DR 场景 masters 全灭亦可推导）。
        # 该机器本身是本单 revoke 候选 → 判据层存活预判天然覆盖：
        #   新 ctl 进程活 → 连新 ctl 查路由残留；进程死 → 证伪短路 NO → 正常回收
        if master_new:
            first_master = master_new[0]
            try:
                _, ctl_port = resolve_spider_ctl_ports(
                    cluster=meta["cluster"],
                    spider_port=info.get("spider_port"),
                    ctl_port=info.get("ctl_port"),
                )
            except ValueError as err:
                raise NormalTenDBFlowException(
                    message="{} infos[{}] resolve spider/ctl ports failed for cluster {}: {}".format(
                        _ERR_PREFIX, info_idx, meta["cluster"].id, err
                    )
                )
            ctl_primary = AccessLayerInstance(
                ip=str(first_master["ip"]),
                port=ctl_port,
                bk_cloud_id=int(first_master.get("bk_cloud_id", 0)),
            )
        else:
            # 仅 slave 段重建：集群存量 spider master 存活，从元数据反查 ctl primary
            # （fail-fast：反查失败直接抛 NormalTenDBFlowException → 单据失败可重试）
            ctl_primary = get_ctl_primary(cluster=meta["cluster"], err_prefix=_ERR_PREFIX, info_idx=info_idx)

        groups: List[ResourceGroup] = []
        for host_idx, host in enumerate(master_new):
            groups.append(
                ResourceGroup(
                    group_id="info_{}_master_{}".format(info_idx, host_idx),
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
            )
        for host_idx, host in enumerate(slave_new):
            groups.append(
                ResourceGroup(
                    group_id="info_{}_slave_{}".format(info_idx, host_idx),
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
            )
        return groups
