# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBCluster 主从成对迁移单据（MIGRATE_CLUSTER）· 候选主机 Extractor。

模块职责：
  - 从 ``TENDBCLUSTER_MIGRATE_CLUSTER`` 单据的 ticket_data 提取每个 info 内"新 master + 新 slave"
    两台机器对应的**单个** :class:`ResourceGroup`
  - 本次只申领新 remote 两台机器（proxy / spider 复用现有，不随本次 revoke 退回）
  - 机器角色硬编码：
      · ``bk_new_master`` → role=remote_master（:attr:`InstanceRole.REMOTE_MASTER`）
      · ``bk_new_slave``  → role=remote_slave（:attr:`InstanceRole.REMOTE_SLAVE`）
  - 端口口径（与 ``TendbClusterMigrateRemoteFlow`` 对齐，端口不在 ticket_data 中）：
      · 新机端口 = **被迁移旧机器**上分片实例（StorageInstance）端口
        （flow 侧由 ``get_master_slave_recover_info`` 从 ``old_master_ip`` / ``old_slave_ip``
        反查，见 ``spider_remote_master_slave_migrate.py`` L162-164）；
        此处读取 old IP **仅用于推导新机 expected_ports**，旧机器本身严禁进入 revoke 候选
  - ``access_layer_proxies``：装入集群 tdbctl 中控 primary（单实例），供 F2.c 判据连 ctl 查
    ``mysql.servers`` 路由残留

分组口径：
  - 一条 info 一组（组内固定 2 unit）：新 master / 新 slave 必须成对绑定（主从依赖关系），
    与 ``MysqlMigrateClusterExtractor``（"新 master + 新 slave 必须成对绑定"）口径对齐

关键字段契约（revoke 入口 ticket_data 来自父单据 ``details["ticket_data"]``）：
  - ``info["cluster_id"]``:     int
  - ``info["bk_new_master"]``:  dict，新 master 主机
  - ``info["bk_new_slave"]``:   dict，新 slave 主机
    （RESOURCE_BATCH_APPLY 按 ``backend_group`` 回填后 post_callback 拆组改名，或
    MANUAL_INPUT 路径直接改名，见 ``mysql_migrate_cluster.py`` L93-109；
    两路径最终均产出 ``bk_new_master`` / ``bk_new_slave`` + ``new_master_ip`` / ``new_slave_ip``）
  - ``info["old_master_ip"]`` / ``info["old_slave_ip"]``: str，旧机器 IP（仅端口推导用）

模块边界：
  - ``infos`` / ``bk_biz_id`` / 单条 info 的通用校验下沉至 :class:`HostExtractor`
  - 本模块只校验本单据特有字段（``bk_new_master`` / ``bk_new_slave`` / ``old_*_ip`` / ``cluster_id``）
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
    get_storage_ports_on_machines,
    load_tendbcluster_meta,
)

#: 日志/异常前缀：便于在 revoke_flow 顶层兜底日志中快速定位来源
_ERR_PREFIX: str = "[SpiderMigrateClusterExtractor]"


class SpiderMigrateClusterExtractor(HostExtractor):
    """TenDBCluster 主从成对迁移单据的候选主机 Extractor。

    职责：
      - 为每个 info 产出一个 :class:`ResourceGroup`，组内固定 2 个 unit
        （新 master = remote_master、新 slave = remote_slave）
      - ``expected_ports`` ← 旧机器（``old_master_ip`` / ``old_slave_ip``）上分片实例端口去重
        （仅端口推导，旧机器不进候选）
      - ``access_layer_proxies`` 装入集群 ctl primary 单实例（供 F2.c tdbctl 路由判据）

    使用方式：
      extractor = SpiderMigrateClusterExtractor()
      groups = extractor.extract(ticket_data)

    线程安全：是（无实例状态）
    边界：
      - ``bk_new_master`` / ``bk_new_slave`` 缺失或缺 ip / bk_host_id → 抛 :class:`NormalTenDBFlowException`
      - ``old_master_ip`` / ``old_slave_ip`` 缺失 → 抛 :class:`NormalTenDBFlowException`
      - 旧机器上反查不到 StorageInstance → 抛 :class:`NormalTenDBFlowException`
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
        """处理单条 info，产出 :class:`ResourceGroup` 单元素列表。

        :param info: 已校验为 dict 的单条 info（含 ``bk_new_master`` / ``bk_new_slave`` / ``old_*_ip``）
        :param info_idx: info 索引
        :param bk_biz_id: 业务 id
        :return: ``[ResourceGroup]``；每条 info 固定产出 1 组、组内 2 unit（主 + 从）
        边界：参见类 docstring
        """
        # 读取新 master / 新 slave 主机信息
        new_master = info.get("bk_new_master")
        new_slave = info.get("bk_new_slave")
        validate_host_dict(host=new_master, err_prefix=_ERR_PREFIX, info_idx=info_idx, field_name="bk_new_master")
        validate_host_dict(host=new_slave, err_prefix=_ERR_PREFIX, info_idx=info_idx, field_name="bk_new_slave")

        # 旧机器 IP（仅用于推导新机 expected_ports；旧机器严禁进入 revoke 候选）
        old_master_ip = info.get("old_master_ip")
        old_slave_ip = info.get("old_slave_ip")
        if not isinstance(old_master_ip, str) or not old_master_ip:
            raise NormalTenDBFlowException(
                message="{} infos[{}].old_master_ip missing: {!r}".format(_ERR_PREFIX, info_idx, old_master_ip)
            )
        if not isinstance(old_slave_ip, str) or not old_slave_ip:
            raise NormalTenDBFlowException(
                message="{} infos[{}].old_slave_ip missing: {!r}".format(_ERR_PREFIX, info_idx, old_slave_ip)
            )

        # 反查 DBM 元数据：旧机器分片实例端口 + ctl primary
        meta: Dict[str, Any] = load_tendbcluster_meta(
            cluster_id=info.get("cluster_id"), err_prefix=_ERR_PREFIX, info_idx=info_idx
        )
        expected_ports: Tuple[int, ...] = get_storage_ports_on_machines(
            cluster=meta["cluster"],
            machine_ips=[old_master_ip, old_slave_ip],
            err_prefix=_ERR_PREFIX,
            info_idx=info_idx,
        )
        ctl_primary = get_ctl_primary(cluster=meta["cluster"], err_prefix=_ERR_PREFIX, info_idx=info_idx)

        # 组内 units：新 master / 新 slave 共享 expected_ports / cluster_type，仅主机 + role 不同
        units: Tuple[RevokeUnit, ...] = tuple(
            RevokeUnit(
                ip=str(host["ip"]),
                bk_host_id=int(host["bk_host_id"]),
                bk_cloud_id=int(host.get("bk_cloud_id", 0)),
                bk_biz_id=bk_biz_id,
                role=role,
                expected_ports=expected_ports,
                cluster_type=ClusterType.TenDBCluster.value,
            )
            for host, role in (
                (new_master, InstanceRole.REMOTE_MASTER.value),
                (new_slave, InstanceRole.REMOTE_SLAVE.value),
            )
        )

        return [
            ResourceGroup(
                group_id="info_{}".format(info_idx),
                units=units,
                cluster_domains=meta["cluster_domains"],
                clb_regions=meta["clb_regions"],
                access_layer_proxies=(ctl_primary,),
            )
        ]
