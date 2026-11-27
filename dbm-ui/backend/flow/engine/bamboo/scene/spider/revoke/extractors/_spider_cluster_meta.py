# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBCluster 集群元数据聚合辅助 · Spider 侧 Extractor 共享实现。

模块职责：
  - 为 spider 侧"仅携带 ``cluster_id`` 的运维单据"（扩容 / 替换 / 升降配 / MNT / 只读接入层 /
    灾难重建 / 迁移升级 / 主从迁移 / 重均衡 / Slave 重建 等）提供统一的 Cluster 元数据反查入口，
    产出 Extractor 装配 :class:`ResourceGroup` 所需的常用字段：
      · ``cluster_domains``      ← ``Cluster.immute_domain``
      · ``clb_regions``          ← ``Cluster.region``（供 F2.b CLB 校验）
      · ``spider_port``          ← 集群级 spider 端口（单值）。结构约定：同集群 spider 端口
        有且只有一个，master / slave / mnt 任意角色共享 → 无需分角色取端口列表，
        取 ``SPIDER_MASTER`` 角色任一实例端口即得（一次查询；每集群必有 ≥1 个
        spider_master，ctl 地址亦由其推导）
      · ``ctl_primary``          ← :meth:`Cluster.tendbcluster_ctl_primary_address` 反查中控
        primary ``(ip, ctl_port, bk_cloud_id)``；remote 侧与 spider 侧单据均消费
        （F2.c tdbctl 路由判据入口）
  - 另提供 ``get_storage_ports_on_machines``：按"旧机器 IP"反查该机器上 remote 分片实例端口，
    供主从迁移 / Slave 重建这类"新机端口 = 旧机分片实例端口"的单据消费

结构约定（本模块端口推导的依据）：
  - 一个集群的 spider 端口有且只有一个，无论 spider master / slave / mnt 什么角色共享同一端口
  - 一台 spider 机器只能属于一个集群 → 集群作用域反查（cluster.proxyinstance_set / storageinstance_set）
    天然满足，不会跨集群污染

设计参考：
  - ``backend/flow/engine/bamboo/scene/mysql/revoke/extractors/_cluster_meta.py``（TenDBHA 版）
  - ``backend/flow/engine/bamboo/scene/spider/spider_add_nodes.py`` 的
    ``SPIDER_MASTER`` 角色实例端口口径（L128-129）

模块边界：
  - ``cluster_id`` 对应集群不存在（已删） → 抛 :class:`NormalTenDBFlowException`
  - 集群无 spider_master 实例（无法推导 spider_port） → 统一在
    :func:`load_tendbcluster_meta` 抛 :class:`NormalTenDBFlowException`（判空收敛到本处，
    上游 Extractor 不再各自判空）
  - ``ctl_primary`` 查不到 RUNNING spider_master（如灾难重建 master 段场景全灭） → 抛
    :class:`NormalTenDBFlowException`（**fail-fast**：构建期报错 → 单据失败可重试，
    好过运行期 MANUAL 挂起——RECYCLE_APPLY_HOST 成功后无法重跑）；DR master 段重建
    单据不经本函数，其 ctl 由 ticket_data 的 ``spider_master_new_ip_list[0]``
    确定性推导（见 ``SpiderLayerDisasterRecoverExtractor``）
  - ``get_storage_ports_on_machines`` 查不到任何 StorageInstance → 抛
    :class:`NormalTenDBFlowException`
  - 异常一律由上层 ``revoke_flow`` 顶层 try/except 统一兜底，本模块不做局部吞异常
"""
from typing import Any, Dict, List, Tuple

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import AccessLayerInstance


def load_tendbcluster_meta(cluster_id: Any, err_prefix: str, info_idx: int) -> Dict[str, Any]:
    """反查 TenDBCluster 集群元数据，产出 Spider 侧 Extractor 组装所需字段。

    设计要点 / 怎么做：
        - 一次 ``Cluster.objects.get`` 拿到 model 实例；``spider_port`` 在该实例的
          related manager 上取（一次查询，无 N+1 风险）
        - 结构约定：同集群 spider 端口有且只有一个（master / slave / mnt 共享），
          取 ``SPIDER_MASTER`` 角色任一实例端口即得；``order_by("id")`` 固定取值口径，
          避免无序 query 在多副本环境下的不确定性

    :param cluster_id: 上游传入的 ``info["cluster_id"]``；期望可整型化
    :param err_prefix: 错误消息前缀，用于区分调用方（如 "[SpiderAddNodesExtractor]"）
    :param info_idx: info 在 infos 中的索引，用于错误消息定位
    :return: dict，字段：
        - ``cluster``:         ``Cluster`` model 实例（上游复用，避免二次反查）
        - ``cluster_domains``:  ``Tuple[str, ...]`` ``Cluster.immute_domain``
        - ``clb_regions``:     ``Tuple[str, ...]`` ``Cluster.region`` 去重（空串过滤）
        - ``spider_port``:     ``int`` 集群级 spider 端口（master / slave / mnt 共享）
    边界：
        - ``cluster_id`` 不可整型化 / 集群不存在 → 抛 :class:`NormalTenDBFlowException`
        - 集群无 ``SPIDER_MASTER`` 实例（无法推导 spider_port） → 抛
          :class:`NormalTenDBFlowException`
    """
    try:
        cluster_id_i: int = int(cluster_id)
    except (TypeError, ValueError) as err:
        raise NormalTenDBFlowException(
            message="{} infos[{}].cluster_id illegal: {!r} ({})".format(err_prefix, info_idx, cluster_id, err)
        )

    try:
        cluster: Cluster = Cluster.objects.get(id=cluster_id_i)
    except Cluster.DoesNotExist:
        raise NormalTenDBFlowException(
            message="{} infos[{}] cluster_id={} not found in DBM meta (removed?)".format(
                err_prefix, info_idx, cluster_id_i
            )
        )

    # 同集群 spider 端口唯一（master/slave/mnt 共享）→ 取 SPIDER_MASTER 任一实例端口即得
    spider_master = (
        cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value)
        .order_by("id")
        .first()
    )
    if spider_master is None:
        raise NormalTenDBFlowException(
            message="{} infos[{}] no SPIDER_MASTER instance to derive spider_port for cluster {}".format(
                err_prefix, info_idx, cluster_id_i
            )
        )

    return {
        "cluster": cluster,
        "cluster_domains": (str(cluster.immute_domain),) if cluster.immute_domain else (),
        "clb_regions": (str(cluster.region),) if cluster.region else (),
        "spider_port": int(spider_master.port),
    }


def get_ctl_primary(cluster: Cluster, err_prefix: str, info_idx: int) -> AccessLayerInstance:
    """反查集群 tdbctl 中控 primary 实例坐标（remote 侧与 spider 侧单据的 F2.c 判据入口；
    解析失败 fail-fast 抛异常，由 revoke_flow 顶层兜底 → 单据失败可重试）。

    设计要点 / 怎么做：
        - 走 :meth:`Cluster.tendbcluster_ctl_primary_address`（"ip:port" 字符串，
          port = spider_port + 1000 的 ctl 口径，见 ``backend/db_meta/models/cluster.py``）
        - ``bk_cloud_id`` 取 ``cluster.bk_cloud_id``：ctl 与集群同云区域（部署契约）

    :param cluster: 已持有 Cluster model 实例（来自 :func:`load_tendbcluster_meta`）
    :param err_prefix: 错误消息前缀
    :param info_idx: info 索引，用于错误消息定位
    :return: :class:`AccessLayerInstance`
    边界：
        - 集群类型非 TenDBCluster / 无 RUNNING spider_master → 底层抛
          :class:`DBMetaException`，此处包装为 :class:`NormalTenDBFlowException`
        - 地址非法（空 / 缺端口） → 抛 :class:`NormalTenDBFlowException`
    """
    try:
        address: str = cluster.tendbcluster_ctl_primary_address()
    except Exception as err:  # DBMetaException：无 RUNNING 中控等
        raise NormalTenDBFlowException(
            message="{} infos[{}] resolve ctl primary failed for cluster {}: {}".format(
                err_prefix, info_idx, cluster.id, err
            )
        )

    parts = str(address).rsplit(":", 1)
    if len(parts) != 2 or not parts[0]:
        raise NormalTenDBFlowException(
            message="{} infos[{}] ctl primary address illegal for cluster {}: {!r}".format(
                err_prefix, info_idx, cluster.id, address
            )
        )
    try:
        ctl_port: int = int(parts[1])
    except (TypeError, ValueError) as err:
        raise NormalTenDBFlowException(
            message="{} infos[{}] ctl primary port illegal for cluster {}: {!r} ({})".format(
                err_prefix, info_idx, cluster.id, parts[1], err
            )
        )

    return AccessLayerInstance(ip=str(parts[0]), port=ctl_port, bk_cloud_id=int(cluster.bk_cloud_id))


def get_storage_ports_on_machines(
    cluster: Cluster, machine_ips: List[str], err_prefix: str, info_idx: int
) -> Tuple[int, ...]:
    """按旧机器 IP 反查该批机器上 remote 分片实例（StorageInstance）端口，去重。

    消费场景（"新机端口 = 旧机分片实例端口"，端口不在 ticket_data 中）：
      - 主从迁移（``old_master_ip`` / ``old_slave_ip``）
      - Slave 重建（``old_slave_ip``）
    注意：本函数只做**端口推导**；旧机器本身严禁进入 revoke 候选（与
    ``MysqlMigrateClusterExtractor`` "严禁读取 old_* 字段（老机器不进候选）" 的口径一致，
    此处读取 old ip 仅用于推导新机 expected_ports）。

    :param cluster: 已持有 Cluster model 实例
    :param machine_ips: 旧机器 IP 列表（上游保证非空）
    :param err_prefix: 错误消息前缀
    :param info_idx: info 索引，用于错误消息定位
    :return: ``Tuple[int, ...]`` 端口去重
    边界：
        - ``machine_ips`` 为空 → 抛 :class:`NormalTenDBFlowException`
        - 反查不到任何 StorageInstance → 抛 :class:`NormalTenDBFlowException`
    """
    ips = [str(ip) for ip in machine_ips or []]
    if not ips:
        raise NormalTenDBFlowException(
            message="{} infos[{}] machine_ips empty: {!r}".format(err_prefix, info_idx, machine_ips)
        )

    ports = {int(si.port) for si in cluster.storageinstance_set.filter(machine__ip__in=ips)}
    if not ports:
        raise NormalTenDBFlowException(
            message="{} infos[{}] no StorageInstance found on machines {} for cluster {}".format(
                err_prefix, info_idx, ips, cluster.id
            )
        )
    return tuple(ports)
