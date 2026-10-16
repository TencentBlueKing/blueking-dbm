# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBCluster 部署单据 · 候选主机 Extractor。

模块职责：
  - 从 ``SPIDER_CLUSTER_APPLY`` 单据的 ticket_data 提取**单个** :class:`ResourceGroup`
  - TenDBCluster apply 单据不支持多集群部署
    （见 ``spider_cluster_deploy.py`` L64 "单据不考虑支持多集群部署情况"），故固定产出 1 组
  - 硬编码机器角色：
      · ``spider_ip_list[i]`` → **单 unit 多端口**：role=spider（来自 role_consts.SPIDER），
        ``expected_ports=(spider_port, ctl_port)``；spider 与 tdbctl 同机同 bk_host_id，
        F1/F2/F4 判据对二者结果等价，F3 元数据判据按 expected_ports 元组一次性反查两个端口的残留，
        避免产出同机双 unit 冗余判定（与 HA proxy 多端口 / Cluster remote 多端口口径对齐）
      · ``remote_group[i]["master"]`` → role=remote_master（来自 InstanceRole.REMOTE_MASTER）；
        ``remote_group[i]["slave"]`` → role=remote_slave（来自 InstanceRole.REMOTE_SLAVE）
  - 端口口径（与 ``TenDBClusterApplyFlow`` 完全对齐）：
      · spider_port = ticket_data["spider_port"]
      · ctl_port    = spider_port + 1000（固定偏移，见 ``spider_cluster_deploy.py`` L94）
      · mysql_ports = (start_mysql_port + i for i in range(remote_shard_num))
        其中 start_mysql_port 固定为 20000（见 ``spider_cluster_deploy.py`` L82）

设计参考：
  - ``backend/flow/engine/bamboo/scene/spider/spider_cluster_deploy.py`` 的 ``TenDBClusterApplyFlow``
  - 参照姐妹实现 ``backend/flow/engine/revoke/extractors/mysql_ha_apply.py``：
    保持异常前缀 / 字段规整 / role 常量命名风格一致

模块边界：
  - ticket_data 关键字段缺失 / 类型非法 -> 直接抛 :class:`NormalTenDBFlowException`，
    由上层 ``revoke_flow`` 顶层 try/except 统一兜底并短路整个 revoke 流程
  - ``remote_group[i].slave`` 可为 None（兼容 ``deploy_cluster_no_slave`` 异形架构），
    此时该 remote tuple 仅产出 remote_master unit，不抛异常
  - 一致性校验口径与 apply flow 入口自身一致：
    ``len(remote_group) * remote_shard_num == cluster_shard_num``（见 ``spider_cluster_deploy.py`` L98-99）
"""
from typing import Any, Dict, List, Tuple

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import AccessLayerInstance, ResourceGroup, RevokeUnit
from backend.flow.engine.bamboo.scene.mysql.revoke.base.role_consts import SPIDER
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors.base import HostExtractor

#: 日志 / 异常前缀：便于在 revoke_flow 顶层兜底日志中快速定位来源
_ERR_PREFIX: str = "[TenDBClusterApplyExtractor]"

#: ctl 端口相对 spider 端口的固定偏移（见 ``spider_cluster_deploy.py`` L94：self.data["ctl_port"] = self.data["spider_port"] + 1000）
_CTL_PORT_OFFSET: int = 1000

#: remote 机器上 mysqld 实例的起始监听端口（见 ``spider_cluster_deploy.py`` L82：self.data["start_mysql_port"] = 20000）
_DEFAULT_START_MYSQL_PORT: int = 20000

#: ResourceGroup.group_id 固定值：TenDBCluster 单据只有一组资源，group_id 保持与 HA/Single 命名风格一致（"apply_info_<idx>"）
_FIXED_GROUP_ID: str = "apply_info_0"


class TenDBClusterApplyExtractor(HostExtractor):
    """TenDBCluster 部署单据的候选主机 Extractor。

    职责：
      - 把 ``SPIDER_CLUSTER_APPLY`` 单据的 ticket_data 映射为**长度固定为 1 的** ``List[ResourceGroup]``
      - 组内 unit 覆盖 3 种角色：spider / remote_master / remote_slave
      - spider 机器采用"单 unit 多端口"模式：一台 spider 机器仅产出 1 个 RevokeUnit，
        ``expected_ports=(spider_port, ctl_port)`` 同时覆盖 spider 与 tdbctl 两个进程端口。
        不再为 ctl 产出独立 unit，理由：
          · spider 与 tdbctl 同机同 ``bk_host_id``，F1/F2/F4 判据对二者结果完全等价，拆分产生冗余
          · F3 判据基于 ``expected_ports`` 过滤 ProxyInstance/StorageInstance，元组内多端口一次反查即可
          · 机器处置动作（RECYCLE/MANUAL/KEEP）是整机维度，不存在同机不同端口判不同结论的场景
          · 与姐妹实现 ``mysql_ha_apply.py`` proxy 多端口 / 本模块 remote 多 shard 的产出口径对齐

    使用方式：
      extractor = TenDBClusterApplyExtractor()
      groups = extractor.extract(ticket_data)  # -> List[ResourceGroup]（长度恒为 1）

    线程安全：是（无实例状态）

    边界：
      - ticket_data 非 dict / 关键字段缺失或类型非法 -> 抛 :class:`NormalTenDBFlowException`
      - spider_ip_list 为空 / remote_group 为空 / 任意机器 dict 缺 ip / bk_host_id -> 抛异常
      - remote_shard_num 非正整数、或 len(remote_group) * remote_shard_num != cluster_shard_num
        -> 抛异常（与 apply flow 入口一致性校验口径对齐）
      - remote_group[i].slave 为 None / 缺失 -> 跳过产出 remote_slave unit（兼容异形架构）
      - 异常一律由上层 revoke_flow 顶层 try/except 统一兜底，本类不做局部吞异常
    """

    def extract(self, ticket_data: Dict) -> List[ResourceGroup]:
        """从 TenDBCluster 部署单据 ticket_data 提取**单个** ResourceGroup。

        设计要点 / 怎么做：
          - 顶层只做 ticket_data 规整、派生字段计算、一致性校验；具体 unit 装配下沉到
            :meth:`_build_single_group`，便于单独测试
          - 关键字段类型规整（int()）保持与姐妹 Extractor (:class:`MysqlHaApplyExtractor`) 一致，
            避免 ticket_data 中字符串类型字段打到 ``start_mysql_port + i`` 时触发 TypeError

        :param ticket_data: SPIDER_CLUSTER_APPLY 单据的 flow ticket_data
        :return: List[ResourceGroup]，长度恒为 1

        边界 / 异常：
          - 解析失败一律 raise :class:`NormalTenDBFlowException`，
            由上层 revoke_flow 顶层 try/except 兜底
        """
        if not isinstance(ticket_data, dict):
            raise NormalTenDBFlowException(
                message="{} ticket_data is not dict: type={}".format(_ERR_PREFIX, type(ticket_data).__name__)
            )

        # ---- 1. 提取关键字段 ----
        spider_ip_list = ticket_data.get("spider_ip_list")
        remote_group = ticket_data.get("remote_group")
        spider_port = ticket_data.get("spider_port")
        remote_shard_num = ticket_data.get("remote_shard_num")
        cluster_shard_num = ticket_data.get("cluster_shard_num")
        immutable_domain = ticket_data.get("immutable_domain")
        bk_biz_id = ticket_data.get("bk_biz_id")
        # start_mysql_port 允许缺省：apply flow 入口构造时固定赋 20000，这里保持兼容
        start_mysql_port = ticket_data.get("start_mysql_port", _DEFAULT_START_MYSQL_PORT)

        # ---- 2. 字段类型 / 存在性校验 ----
        if not isinstance(spider_ip_list, list) or not spider_ip_list:
            raise NormalTenDBFlowException(
                message="{} ticket_data.spider_ip_list empty or non-list: {!r}".format(_ERR_PREFIX, spider_ip_list)
            )
        if not isinstance(remote_group, list) or not remote_group:
            raise NormalTenDBFlowException(
                message="{} ticket_data.remote_group empty or non-list: {!r}".format(_ERR_PREFIX, remote_group)
            )
        if not isinstance(immutable_domain, str) or not immutable_domain:
            raise NormalTenDBFlowException(
                message="{} ticket_data.immutable_domain missing or empty: {!r}".format(_ERR_PREFIX, immutable_domain)
            )

        # 类型规整（ticket_data 里可能是字符串）
        try:
            spider_port_i: int = int(spider_port)
            remote_shard_num_i: int = int(remote_shard_num)
            cluster_shard_num_i: int = int(cluster_shard_num)
            bk_biz_id_i: int = int(bk_biz_id)
            start_mysql_port_i: int = int(start_mysql_port)
        except (TypeError, ValueError) as err:
            raise NormalTenDBFlowException(message="{} ticket_data field types illegal: {}".format(_ERR_PREFIX, err))

        # ---- 3. 一致性校验（与 apply flow 入口口径对齐，见 spider_cluster_deploy.py L98-99）----
        if remote_shard_num_i <= 0:
            raise NormalTenDBFlowException(
                message="{} remote_shard_num must be positive int, got {}".format(_ERR_PREFIX, remote_shard_num_i)
            )
        if len(remote_group) * remote_shard_num_i != cluster_shard_num_i:
            raise NormalTenDBFlowException(
                message=(
                    "{} shard num mismatch: len(remote_group)={} * remote_shard_num={} != cluster_shard_num={}"
                ).format(_ERR_PREFIX, len(remote_group), remote_shard_num_i, cluster_shard_num_i)
            )

        # ---- 4. 计算派生字段 ----
        ctl_port_i: int = spider_port_i + _CTL_PORT_OFFSET
        # spider 机器单 unit 多端口：expected_ports 同时覆盖 spider_port 与 ctl_port，
        # F3 元数据判据会按元组逐端口反查 ProxyInstance 残留
        spider_ports: Tuple[int, ...] = (spider_port_i, ctl_port_i)
        mysql_ports: Tuple[int, ...] = tuple(start_mysql_port_i + i for i in range(remote_shard_num_i))

        # F2.b CLB region：部署类单据直接取 ticket_data["city"]（Cluster 尚未入库，不能走 Cluster.region）；
        # 非字符串 / 空串时降级为空元组（下游 check_clb_mapping 遇空返回 NO_REGION_INPUT）
        city = ticket_data.get("city")
        clb_regions: Tuple[str, ...] = (city.strip(),) if isinstance(city, str) and city.strip() else ()

        # ---- 5. 装配单组并返回 ----
        group: ResourceGroup = self._build_single_group(
            spider_ip_list=spider_ip_list,
            remote_group=remote_group,
            spider_ports=spider_ports,
            mysql_ports=mysql_ports,
            ctl_port=ctl_port_i,
            immutable_domain=immutable_domain,
            bk_biz_id=bk_biz_id_i,
            clb_regions=clb_regions,
        )
        return [group]

    def _build_single_group(
        self,
        spider_ip_list: List[Dict[str, Any]],
        remote_group: List[Dict[str, Any]],
        spider_ports: Tuple[int, ...],
        mysql_ports: Tuple[int, ...],
        ctl_port: int,
        immutable_domain: str,
        bk_biz_id: int,
        clb_regions: Tuple[str, ...],
    ) -> ResourceGroup:
        """装配单个 ResourceGroup：spider 单 unit（多端口）+ remote master/slave unit。

        设计要点 / 怎么做：
          - spider 机器每台产出 **1 个 unit**：role=spider，
            ``expected_ports=(spider_port, ctl_port)``；tdbctl 不再独立产出 unit
            （同机同 bk_host_id，F1/F2/F4 冗余，F3 单元组内多端口反查即可）
          - remote tuple 的 master 必产出 remote_master unit；slave 存在时额外产出 remote_slave unit
            （兼容 ``deploy_cluster_no_slave`` 异形架构，见 ``spider_cluster_deploy.py`` L104-105）
          - 首台 spider 机器（``spider_ip_list[0]``）即 ctl_primary，装入 ``access_layer_proxies``
            供 F2.c 走 ctl 查 ``mysql.servers``（与 unit 层解耦）
          - 所有 unit 的 ``cluster_type`` 固定为 ``ClusterType.TenDBCluster.value``，
            使 F1 判据的 ``ClusterTypeMachineTypeDefine[cluster_type]`` 反查天然命中

        :param spider_ip_list: ticket_data.spider_ip_list
        :param remote_group: ticket_data.remote_group
        :param spider_ports: (spider_port, ctl_port) 二元组，spider 机器 unit 的 expected_ports
        :param mysql_ports: tuple(start_mysql_port + i for i in range(remote_shard_num))
        :param ctl_port: ctl 端口，用于构造 ctl_primary 的 AccessLayerInstance.port
        :param immutable_domain: 集群主域名，用作 ResourceGroup.cluster_domains 唯一元素
        :param bk_biz_id: 业务 id
        :return: 单个 :class:`ResourceGroup`

        边界 / 异常：
          - spider_ip_list 任一元素非 dict / 缺 ip / 缺 bk_host_id -> 抛 :class:`NormalTenDBFlowException`
          - remote_group 任一元素非 dict / master 缺字段 -> 抛 :class:`NormalTenDBFlowException`
          - remote_group[i].slave 为 None / 缺失 / 非 dict / 缺 ip / 缺 bk_host_id
            -> **跳过**产出 remote_slave unit，不抛异常（兼容异形架构）
        """
        units: List[RevokeUnit] = []

        # ---- Spider 单 unit 多端口产出：每台 spider 机器 → 1 条 role=SPIDER 的 unit（expected_ports 同时覆盖 spider_port 与 ctl_port）----
        # 首台 spider 机器（spider_ip_list[0]）即 ctl_primary，提前构造 access_layer_proxies 唯一元素
        # （见 spider_cluster_deploy.py L221：``ctl_master = self.data["spider_ip_list"][0]``）
        # spider_ip_list 已在 extract() 校验非空，此处 [0] 必然可取；字段校验与循环体保持一致以维护异常 message 格式
        first_sp = spider_ip_list[0]
        if not isinstance(first_sp, dict) or "ip" not in first_sp or "bk_host_id" not in first_sp:
            raise NormalTenDBFlowException(
                message="{} spider_ip_list[0] missing ip/bk_host_id: {!r}".format(_ERR_PREFIX, first_sp)
            )
        ctl_primary_instance: AccessLayerInstance = AccessLayerInstance(
            ip=str(first_sp["ip"]),
            port=ctl_port,
            bk_cloud_id=int(first_sp.get("bk_cloud_id", 0)),
        )

        for idx, sp in enumerate(spider_ip_list):
            if not isinstance(sp, dict) or "ip" not in sp or "bk_host_id" not in sp:
                raise NormalTenDBFlowException(
                    message="{} spider_ip_list[{}] missing ip/bk_host_id: {!r}".format(_ERR_PREFIX, idx, sp)
                )
            # spider 单 unit：expected_ports 同时包含 spider_port 与 ctl_port，F3 一次性反查两端口残留
            units.append(
                RevokeUnit(
                    ip=str(sp["ip"]),
                    bk_host_id=int(sp["bk_host_id"]),
                    bk_cloud_id=int(sp.get("bk_cloud_id", 0)),
                    bk_biz_id=bk_biz_id,
                    role=SPIDER,
                    expected_ports=spider_ports,
                    cluster_type=ClusterType.TenDBCluster.value,
                )
            )

        # ---- Remote unit 产出：每组 tuple → master（必产）+ slave（可选）----
        for idx, pair in enumerate(remote_group):
            if not isinstance(pair, dict):
                raise NormalTenDBFlowException(
                    message="{} remote_group[{}] is not dict: {!r}".format(_ERR_PREFIX, idx, pair)
                )

            master = pair.get("master")
            if not isinstance(master, dict) or "ip" not in master or "bk_host_id" not in master:
                raise NormalTenDBFlowException(
                    message="{} remote_group[{}].master missing ip/bk_host_id: {!r}".format(_ERR_PREFIX, idx, master)
                )
            units.append(
                RevokeUnit(
                    ip=str(master["ip"]),
                    bk_host_id=int(master["bk_host_id"]),
                    bk_cloud_id=int(master.get("bk_cloud_id", 0)),
                    bk_biz_id=bk_biz_id,
                    role=InstanceRole.REMOTE_MASTER.value,
                    expected_ports=mysql_ports,
                    cluster_type=ClusterType.TenDBCluster.value,
                )
            )

            # slave 兼容异形架构（deploy_cluster_no_slave）：缺失 / None / 非 dict / 缺字段 一律跳过（不抛异常）
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

        return ResourceGroup(
            group_id=_FIXED_GROUP_ID,
            units=tuple(units),
            cluster_domains=(immutable_domain,),
            clb_regions=clb_regions,
            access_layer_proxies=(ctl_primary_instance,),
        )
