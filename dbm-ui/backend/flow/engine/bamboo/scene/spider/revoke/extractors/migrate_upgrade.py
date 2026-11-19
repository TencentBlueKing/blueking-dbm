# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBCluster 存储层迁移升级单据（MIGRATE_UPGRADE）/ 存储层重均衡单据（NODE_REBALANCE）·
候选主机 Extractor。

两单据的 ticket_data 完全同构，共用本实现；``node_rebalance.py`` 以子类
``SpiderNodeRebalanceExtractor``（仅覆盖 ``_err_prefix``，其余完全继承）引用本类。

模块职责：
  - 从 ``TENDBCLUSTER_MIGRATE_UPGRADE``（存储层**迁移**升级）单据的 ticket_data 提取每个 info 内
    每对"新 master + 新 slave"机器对应的 :class:`ResourceGroup`
  - 本单据固定迁移升级模式（本地升级是独立单据 ``TENDBCLUSTER_REMOTE_UPGRADE`` 且未注册
    ``is_apply``，终止不会触发本 revoke）；本次只申领新 remote 一批机器顶替旧节点，
    旧节点的下架不进本 revoke 候选
  - 机器角色硬编码：
      · ``remote_group[i]["master"]`` → role=remote_master（:attr:`InstanceRole.REMOTE_MASTER`）
      · ``remote_group[i]["slave"]``  → role=remote_slave（:attr:`InstanceRole.REMOTE_SLAVE`）
  - 端口口径（与 ``TenDBClusterStorageMigrateUpgradeFlow`` 对齐，见 ``migrate_upgrade.py``
    L189 / L227-229）：mysql_ports = ``range(20000, 20000 + remote_shard_num)``

分组口径（关键设计点）：
  - 单条 info 内的 N 对"新 master + 新 slave"**每对独立成组**（一组 2 unit）：主从成对绑定
    （新 master / 新 slave 必须成对迁移），与 ``MysqlMigrateClusterExtractor``
    （"新 master + 新 slave 必须成对绑定"）口径对齐；对与对之间相互独立

关键字段契约（revoke 入口 ticket_data 来自父单据 ``details["ticket_data"]``）：
  - ``info["cluster_id"]``:       int
  - ``info["remote_group"]``:      ``List[dict]``，每项 ``{"master": host, "slave": host}``
    （RESOURCE_BATCH_APPLY 按 ``backend_group`` 角色回填后，post_callback 改名为
    ``remote_group``，见 ``tendb_migrate_upgrade.py``）
  - ``info["remote_shard_num"]``:  int，每对机器承载的分片数
  - ``access_layer_proxies``：装入集群 tdbctl 中控 primary（单实例），供 F2.c 判据连 ctl 查
    ``mysql.servers`` 路由残留（remote_master / remote_slave 均在 tdbctl 路由表内）

模块边界：
  - ``infos`` / ``bk_biz_id`` / 单条 info 的通用校验下沉至 :class:`HostExtractor`
  - 本模块只校验本单据特有字段（``remote_group`` / ``remote_shard_num`` / ``cluster_id``）
  - ``remote_group[i].slave`` 缺失 / 非 dict / 缺字段 → **跳过**产出 remote_slave unit，
    不抛异常（与 ``TenDBClusterApplyExtractor`` 的异形架构兼容口径一致）
  - 校验失败一律抛 :class:`NormalTenDBFlowException`，由上层 ``revoke_flow`` 顶层 try/except 兜底
"""
from typing import Any, Dict, List, Tuple

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import ResourceGroup, RevokeUnit
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors._cluster_meta import validate_host_dict
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors.base import HostExtractor
from backend.flow.engine.bamboo.scene.spider.revoke.extractors._spider_cluster_meta import (
    get_ctl_primary,
    load_tendbcluster_meta,
)

#: 日志/异常前缀：便于在 revoke_flow 顶层兜底日志中快速定位来源。
#: 实现内一律消费 ``self._err_prefix``（不直接引用本常量），供子类（如
#: ``SpiderNodeRebalanceExtractor``）按单据类型覆盖
_ERR_PREFIX: str = "[TenDBClusterMigrateUpgradeExtractor]"

#: remote 机器上 mysqld 实例的起始监听端口（见 ``spider_remotedb_rebalance_flow.py`` L108 /
#: ``migrate_upgrade.py`` L189：``start_port = 20000``）
_DEFAULT_START_MYSQL_PORT: int = 20000


def _pair_units(
    pair: Any,
    pair_idx: int,
    info_idx: int,
    bk_biz_id: int,
    mysql_ports: Tuple[int, ...],
    err_prefix: str,
) -> Tuple[RevokeUnit, ...]:
    """装配一对 ``{"master": host, "slave": host}`` 的 RevokeUnit 列表（remote 侧单据共享）。

    :param pair: remote 组（期望 dict）
    :param pair_idx: 组内索引（错误消息定位）
    :param info_idx: info 索引（错误消息定位）
    :param bk_biz_id: 业务 id
    :param mysql_ports: 本单在该机器上申领的分片端口列表
    :param err_prefix: 错误消息前缀（调用方Extractor 前缀）
    :return: ``(remote_master unit, ...)``；master 必产，slave 存在时额外产出
    边界：
      - pair 非 dict / master 缺字段 → 抛 :class:`NormalTenDBFlowException`
      - slave 缺失 / 非 dict / 缺字段 → 跳过（兼容 backend_group 无 slave 的异形场景）
    """
    if not isinstance(pair, dict):
        raise NormalTenDBFlowException(
            message="{} infos[{}].remote_group[{}] is not dict: {!r}".format(err_prefix, info_idx, pair_idx, pair)
        )
    master = pair.get("master")
    validate_host_dict(
        host=master, err_prefix=err_prefix, info_idx=info_idx, field_name="remote_group[{}].master".format(pair_idx)
    )
    units: List[RevokeUnit] = [
        RevokeUnit(
            ip=str(master["ip"]),
            bk_host_id=int(master["bk_host_id"]),
            bk_cloud_id=int(master.get("bk_cloud_id", 0)),
            bk_biz_id=bk_biz_id,
            role=InstanceRole.REMOTE_MASTER.value,
            expected_ports=mysql_ports,
            cluster_type=ClusterType.TenDBCluster.value,
        )
    ]
    slave = pair.get("slave")
    if isinstance(slave, dict) and "ip" in slave and "bk_host_id" in slave:
        units.append(
            RevokeUnit(
                ip=str(slave["ip"]),
                bk_host_id=int(slave["bk_host_id"]),
                bk_cloud_id=int(slave.get("bk_cloud_id", 0)),
                bk_biz_id=bk_biz_id,
                role=InstanceRole.REMOTE_SLAVE.value,
                expected_ports=mysql_ports,
                cluster_type=ClusterType.TenDBCluster.value,
            )
        )
    return tuple(units)


class TenDBClusterMigrateUpgradeExtractor(HostExtractor):
    """TenDBCluster 存储层迁移升级单据的候选主机 Extractor。

    职责：
      - 为单条 info 内的每对"新 master + 新 slave"产出**一个独立** :class:`ResourceGroup`
        （组内 1~2 个 unit）；一个 info 的 N 对机器 → N 个 ResourceGroup
      - ``expected_ports = tuple(range(20000, 20000 + remote_shard_num))``
      - ``access_layer_proxies`` 装入集群 ctl primary 单实例（供 F2.c tdbctl 路由判据）

    使用方式：
      extractor = TenDBClusterMigrateUpgradeExtractor()
      groups = extractor.extract(ticket_data)

    线程安全：是（无实例状态）
    边界：
      - ``remote_group`` 为空 / 非 list → 抛 :class:`NormalTenDBFlowException`
      - ``remote_shard_num`` 非正整数 → 抛 :class:`NormalTenDBFlowException`
      - ctl primary 解析失败 → 抛 :class:`NormalTenDBFlowException`
    """

    #: 日志/异常前缀：供基类统一错误消息使用
    _err_prefix: str = _ERR_PREFIX

    def _extract_one_info(
        self,
        info: Dict[str, Any],
        info_idx: int,
        bk_biz_id: int,
    ) -> List[ResourceGroup]:
        """处理单条 info，为内部每对"新 master + 新 slave"产出独立 :class:`ResourceGroup`。

        :param info: 已校验为 dict 的单条 info（含 ``cluster_id`` / ``remote_group`` / ``remote_shard_num``）
        :param info_idx: info 索引
        :param bk_biz_id: 业务 id
        :return: ``List[ResourceGroup]``；长度 = len(remote_group)，每组 1~2 个 unit
        边界：参见类 docstring
        """
        remote_group = info.get("remote_group")
        if not isinstance(remote_group, list) or not remote_group:
            raise NormalTenDBFlowException(
                message="{} infos[{}].remote_group empty or non-list: {!r}".format(
                    self._err_prefix, info_idx, remote_group
                )
            )

        try:
            remote_shard_num: int = int(info.get("remote_shard_num"))
        except (TypeError, ValueError) as err:
            raise NormalTenDBFlowException(
                message="{} infos[{}].remote_shard_num illegal: {!r} ({})".format(
                    self._err_prefix, info_idx, info.get("remote_shard_num"), err
                )
            )
        if remote_shard_num <= 0:
            raise NormalTenDBFlowException(
                message="{} infos[{}].remote_shard_num must be positive int, got {}".format(
                    self._err_prefix, info_idx, remote_shard_num
                )
            )

        # 反查 DBM 元数据：ctl primary（F2.c 判据入口）
        meta: Dict[str, Any] = load_tendbcluster_meta(
            cluster_id=info.get("cluster_id"), err_prefix=self._err_prefix, info_idx=info_idx
        )
        ctl_primary = get_ctl_primary(cluster=meta["cluster"], err_prefix=self._err_prefix, info_idx=info_idx)

        mysql_ports: Tuple[int, ...] = tuple(
            range(_DEFAULT_START_MYSQL_PORT, _DEFAULT_START_MYSQL_PORT + remote_shard_num)
        )

        # 一对一组：N 对新主从 → N 个 ResourceGroup；group_id 用 "info_{i}_pair_{j}" 保证全局唯一
        return [
            ResourceGroup(
                group_id="info_{}_pair_{}".format(info_idx, pair_idx),
                units=_pair_units(
                    pair=pair,
                    pair_idx=pair_idx,
                    info_idx=info_idx,
                    bk_biz_id=bk_biz_id,
                    mysql_ports=mysql_ports,
                    err_prefix=self._err_prefix,
                ),
                cluster_domains=meta["cluster_domains"],
                clb_regions=meta["clb_regions"],
                access_layer_proxies=(ctl_primary,),
            )
            for pair_idx, pair in enumerate(remote_group)
        ]
