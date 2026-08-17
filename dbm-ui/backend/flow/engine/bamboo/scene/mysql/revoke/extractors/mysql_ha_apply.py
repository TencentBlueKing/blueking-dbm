# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBHA 部署单据 · 候选主机 Extractor。

模块职责：
  - 从 ``MYSQL_HA_APPLY`` 单据的 ticket_data 提取每个 apply_info 对应的 :class:`ResourceGroup`
  - 硬编码机器角色：``proxy_ip_list`` → role=proxy（来自 role_consts.PROXY）；
    ``mysql_ip_list[0]`` → role=backend_master（来自 InstanceRole.BACKEND_MASTER）；
    ``mysql_ip_list[1]`` → role=backend_slave（来自 InstanceRole.BACKEND_SLAVE）
  - 端口计算依据 ``mysql_ha_apply_flow`` 一致：``min(inst_num, len(clusters))`` 个 (port_start + i)
  - 域名分配：proxy 绑 ``clusters[*].master``；backend_slave 绑 ``clusters[*].slave``；backend_master 不绑
  - F2.d admin 探测端口：装入 ``ResourceGroup.access_layer_proxies`` 的 port 字段必须是
    mysql-proxy 的 **admin 端口（= start_proxy_port + 1000）**，而非 SQL 服务端口；
    依据 ``db_meta/api/proxy_instance/apis.py`` 创建 ProxyInstance 时硬编码的
    ``admin_port = proxy_port + 1000`` 约束

设计参考：
  - ``backend/flow/engine/bamboo/scene/mysql/mysql_ha_apply_flow.py`` 的 ``deploy_mysql_ha_flow_with_manual``
  - 每 apply_info 一组，组间独立、组内绑定

模块边界：
  - ticket_data 关键字段缺失 / 类型非法 -> 直接抛 :class:`NormalTenDBFlowException`，
    由上层 ``revoke_flow`` 顶层 try/except 统一兜底并短路整个 revoke 流程
  - apply_infos 为空列表 -> 返回 []（正常场景，允许无候选组）
"""
from typing import Any, Dict, List, Tuple

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import AccessLayerInstance, ResourceGroup, RevokeUnit
from backend.flow.engine.bamboo.scene.mysql.revoke.base.role_consts import PROXY
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors.base import HostExtractor

#: 日志/异常前缀：便于在 revoke_flow 顶层兜底日志中快速定位来源
_ERR_PREFIX: str = "[MysqlHaApplyExtractor]"

#: TenDBHA · mysql-proxy admin port 相对 proxy_port 的固定偏移量；单位：端口号
#: 依据：``db_meta/api/proxy_instance/apis.py`` 创建 ProxyInstance 时硬编码
#:   ``admin_port = proxy_port + 1000``；全仓无例外（spider 中控 ``tdbctl.admin_port``
#:   亦走同样 +1000 兜底规则）。本常量在 Extractor 侧显式声明，避免散字符串偏移漂移。
#: 用途：F2.d 判据对 proxy 发起 ``DRSApi.proxyrpc SELECT * FROM backends;``
#:   走的是 mysql-proxy 的 **management 协议端口（admin port）**，不是对客户端 SQL 协议端口；
#:   若装入 ``AccessLayerInstance.port`` 的是 proxy_port（SQL 口），proxyrpc 会协议错误
#:   → F2.d 判 UNKNOWN → BACKEND_MASTER 走 MANUAL 挂起，整组误判为 GROUP_MANUAL
_PROXY_ADMIN_PORT_OFFSET: int = 1000


class MysqlHaApplyExtractor(HostExtractor):
    """TenDBHA 部署单据的候选主机 Extractor。

    职责：
      - 遍历 ``ticket_data["apply_infos"]``，为每个 apply_info 产出一个 ResourceGroup
      - 每组机器角色硬编码（proxy / backend_master / backend_slave）
      - 端口按 ``start_proxy_port + i`` / ``start_mysql_port + i`` 展开，
        i ∈ range(min(inst_num, len(clusters)))

    使用方式：
      extractor = MysqlHaApplyExtractor()
      groups = extractor.extract(ticket_data)

    线程安全：是
    边界：
      - ticket_data 类型非 dict / 关键字段（apply_infos / start_proxy_port / start_mysql_port /
        inst_num / bk_biz_id）缺失或类型非法 -> 抛 :class:`NormalTenDBFlowException`
      - 单个 apply_info 缺关键字段（proxy_ip_list / mysql_ip_list / clusters 等）或
        mysql_ip_list 长度不足 2 -> 抛 :class:`NormalTenDBFlowException`
      - 异常一律由上层 ``revoke_flow`` 顶层 try/except 统一兜底，本类不做局部吞异常
    """

    def extract(self, ticket_data: Dict) -> List[ResourceGroup]:
        """从 TenDBHA 部署单据 ticket_data 提取候选组列表。

        :param ticket_data: MYSQL_HA_APPLY 单据的 flow ticket_data
        :return: List[ResourceGroup]；apply_infos 为空列表时返回 []
        边界：解析失败一律 raise :class:`NormalTenDBFlowException`，
              由上层 revoke_flow 顶层 try/except 兜底
        """
        if not isinstance(ticket_data, dict):
            raise NormalTenDBFlowException(
                message="{} ticket_data is not dict: type={}".format(_ERR_PREFIX, type(ticket_data).__name__)
            )

        apply_infos = ticket_data.get("apply_infos")
        if not isinstance(apply_infos, list):
            raise NormalTenDBFlowException(
                message="{} ticket_data.apply_infos missing or not list: {!r}".format(_ERR_PREFIX, apply_infos)
            )

        start_proxy_port = ticket_data.get("start_proxy_port")
        start_mysql_port = ticket_data.get("start_mysql_port")
        inst_num = ticket_data.get("inst_num")
        bk_biz_id = ticket_data.get("bk_biz_id")

        # 类型规整（ticket_data 里可能是字符串）
        try:
            start_proxy_port_i: int = int(start_proxy_port)
            start_mysql_port_i: int = int(start_mysql_port)
            inst_num_i: int = int(inst_num)
            bk_biz_id_i: int = int(bk_biz_id)
        except (TypeError, ValueError) as err:
            raise NormalTenDBFlowException(message="{} ticket_data field types illegal: {}".format(_ERR_PREFIX, err))

        # F2.b CLB region：部署类单据直接取 ticket_data["city"]（Cluster 尚未入库，不能走 Cluster.region）；
        # 非字符串 / 空串时降级为空元组（下游 check_clb_mapping 遇空返回 NO_REGION_INPUT）
        city = ticket_data.get("city")
        clb_regions: Tuple[str, ...] = (city.strip(),) if isinstance(city, str) and city.strip() else ()

        groups: List[ResourceGroup] = []
        for idx, info in enumerate(apply_infos):
            group = self._extract_one_apply_info(
                apply_info=info,
                apply_info_idx=idx,
                start_proxy_port=start_proxy_port_i,
                start_mysql_port=start_mysql_port_i,
                inst_num=inst_num_i,
                bk_biz_id=bk_biz_id_i,
                clb_regions=clb_regions,
            )
            groups.append(group)
        return groups

    def _extract_one_apply_info(
        self,
        apply_info: Dict[str, Any],
        apply_info_idx: int,
        start_proxy_port: int,
        start_mysql_port: int,
        inst_num: int,
        bk_biz_id: int,
        clb_regions: Tuple[str, ...],
    ) -> ResourceGroup:
        """处理一个 apply_info，产出 ResourceGroup。

        :param apply_info: 单个 apply_info 字典
        :param apply_info_idx: apply_info 在 apply_infos 中的索引，用于组 group_id 构造
        :param start_proxy_port: ticket_data.start_proxy_port
        :param start_mysql_port: ticket_data.start_mysql_port
        :param inst_num: ticket_data.inst_num
        :param bk_biz_id: 业务 id
        :return: :class:`ResourceGroup`
        边界：
          - apply_info 类型非 dict -> 抛 :class:`NormalTenDBFlowException`
          - proxy_ip_list / mysql_ip_list / clusters 任一非 list 或空 -> 抛 :class:`NormalTenDBFlowException`
          - mysql_ip_list 长度 < 2 -> 抛 :class:`NormalTenDBFlowException`（HA 至少 1 master + 1 slave）
          - proxy/mysql 明细缺 ip / bk_host_id -> 抛 :class:`NormalTenDBFlowException`
        """
        if not isinstance(apply_info, dict):
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}] is not dict: {!r}".format(_ERR_PREFIX, apply_info_idx, apply_info)
            )

        proxy_ip_list = apply_info.get("proxy_ip_list") or []
        mysql_ip_list = apply_info.get("mysql_ip_list") or []
        clusters = apply_info.get("clusters") or []

        if not isinstance(proxy_ip_list, list) or not proxy_ip_list:
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}].proxy_ip_list empty or non-list".format(_ERR_PREFIX, apply_info_idx)
            )
        if not isinstance(mysql_ip_list, list) or len(mysql_ip_list) < 2:
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}].mysql_ip_list length < 2 (got {})".format(
                    _ERR_PREFIX,
                    apply_info_idx,
                    len(mysql_ip_list) if isinstance(mysql_ip_list, list) else "non-list",
                )
            )
        if not isinstance(clusters, list) or not clusters:
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}].clusters empty or non-list".format(_ERR_PREFIX, apply_info_idx)
            )

        # 计算实际部署端口数量（与 mysql_ha_apply_flow.py 对齐）
        actual_inst_count: int = min(inst_num, len(clusters))
        if actual_inst_count <= 0:
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}] actual_inst_count <= 0 (inst_num={} clusters={})".format(
                    _ERR_PREFIX, apply_info_idx, inst_num, len(clusters)
                )
            )

        proxy_ports: Tuple[int, ...] = tuple(start_proxy_port + i for i in range(actual_inst_count))
        mysql_ports: Tuple[int, ...] = tuple(start_mysql_port + i for i in range(actual_inst_count))

        # 提取集群主域名列表（顺序对齐 clusters[*].master；slave 域名不进 revoke 判定，不收集）
        cluster_domains: Tuple[str, ...] = tuple(
            c["master"] for c in clusters if isinstance(c, dict) and c.get("master")
        )

        # ---- 构造组内 units ----
        units: List[RevokeUnit] = []

        # Proxy 单元：一台机器多实例，绑定所有 master 域名
        #   同时装配本组的 access_layer_proxies（长度 = len(proxy_ip_list)），供 F2.d 走 proxy 后端查询
        access_layer_proxies: List[AccessLayerInstance] = []
        for p in proxy_ip_list:
            if not isinstance(p, dict) or "ip" not in p or "bk_host_id" not in p:
                raise NormalTenDBFlowException(
                    message="{} apply_infos[{}].proxy_ip_list item missing ip/bk_host_id: {!r}".format(
                        _ERR_PREFIX, apply_info_idx, p
                    )
                )
            proxy_bk_cloud_id: int = int(p.get("bk_cloud_id", 0))
            units.append(
                RevokeUnit(
                    ip=str(p["ip"]),
                    bk_host_id=int(p["bk_host_id"]),
                    bk_cloud_id=proxy_bk_cloud_id,
                    bk_biz_id=bk_biz_id,
                    role=PROXY,
                    expected_ports=proxy_ports,
                    cluster_type=ClusterType.TenDBHA.value,
                )
            )
            # F2.d 探测入口：port 必须填 proxy 的 **admin 端口（管理协议口）** = start_proxy_port + 1000
            # 原因：F2.d 走 ``DRSApi.proxyrpc`` 发送 ``SELECT * FROM backends;`` 查后端引用，
            #       mysql-proxy 对此命令只在 admin port 上响应；若误填 start_proxy_port（SQL 服务口）
            #       会直接导致 proxyrpc 协议错误 → F2.d UNKNOWN → BACKEND_MASTER 走 MANUAL
            # 多实例口径：Extractor 契约按 start_proxy_port 为唯一 admin 探测挖子（admin port 不随
            #       inst_num 展开，mysql-proxy admin 端口在一台机器上只有一个）
            access_layer_proxies.append(
                AccessLayerInstance(
                    ip=str(p["ip"]),
                    port=start_proxy_port + _PROXY_ADMIN_PORT_OFFSET,
                    bk_cloud_id=proxy_bk_cloud_id,
                )
            )

        # Backend master 单元（mysql_ip_list[0]）：不绑域名
        m = mysql_ip_list[0]
        if not isinstance(m, dict) or "ip" not in m or "bk_host_id" not in m:
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}].mysql_ip_list[0] missing ip/bk_host_id".format(_ERR_PREFIX, apply_info_idx)
            )
        units.append(
            RevokeUnit(
                ip=str(m["ip"]),
                bk_host_id=int(m["bk_host_id"]),
                bk_cloud_id=int(m.get("bk_cloud_id", 0)),
                bk_biz_id=bk_biz_id,
                role=InstanceRole.BACKEND_MASTER.value,
                expected_ports=mysql_ports,
                cluster_type=ClusterType.TenDBHA.value,
            )
        )

        # Backend slave 单元（mysql_ip_list[1]）：绑 slave 域名
        s = mysql_ip_list[1]
        if not isinstance(s, dict) or "ip" not in s or "bk_host_id" not in s:
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}].mysql_ip_list[1] missing ip/bk_host_id".format(_ERR_PREFIX, apply_info_idx)
            )
        units.append(
            RevokeUnit(
                ip=str(s["ip"]),
                bk_host_id=int(s["bk_host_id"]),
                bk_cloud_id=int(s.get("bk_cloud_id", 0)),
                bk_biz_id=bk_biz_id,
                role=InstanceRole.BACKEND_SLAVE.value,
                expected_ports=mysql_ports,
                cluster_type=ClusterType.TenDBHA.value,
            )
        )

        return ResourceGroup(
            group_id="apply_info_{}".format(apply_info_idx),
            units=tuple(units),
            cluster_domains=cluster_domains,
            clb_regions=clb_regions,
            access_layer_proxies=tuple(access_layer_proxies),
        )
