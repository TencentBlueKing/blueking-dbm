# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBSingle 部署单据 · 候选主机 Extractor。

模块职责：
  - 从 ``MYSQL_SINGLE_APPLY`` 单据的 ticket_data 提取每个 apply_info 对应的 :class:`ResourceGroup`
  - 硬编码机器角色：``new_ip`` → role=orphan（TenDBSingle 架构不含 proxy 层，也无主从；影射 ``InstanceRole.ORPHAN``）
  - 端口计算依据 ``mysql_single_apply_flow`` 一致：``min(inst_num, len(clusters))`` 个 (start_mysql_port + i)
  - 域名分配：single 机器绑 ``clusters[*].master``（Single 只有主域名，无 slave 域名）

设计参考：
  - ``backend/flow/engine/bamboo/scene/mysql/mysql_single_apply_flow.py`` 的 ``deploy_mysql_single_flow``
  - 每 apply_info 对应 1 台 single 机器 + M 个 Single 集群实例，作为一个 ResourceGroup
  - 一组一台，组间独立并行；G1（组内一致性）单元素天然成立

模块边界：
  - ticket_data 关键字段缺失 / 类型非法 -> 直接抛 :class:`NormalTenDBFlowException`，
    由上层 ``revoke_flow`` 顶层 try/except 统一兜底并短路整个 revoke 流程
  - apply_infos 为空列表 -> 返回 []（正常场景，允许无候选组）
"""
from typing import Any, Dict, List, Tuple

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import ResourceGroup, RevokeUnit
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors.base import HostExtractor

#: 日志/异常前缀：便于在 revoke_flow 顶层兜底日志中快速定位来源
_ERR_PREFIX: str = "[MysqlSingleApplyExtractor]"


class MysqlSingleApplyExtractor(HostExtractor):
    """TenDBSingle 部署单据的候选主机 Extractor。

    职责：
      - 遍历 ``ticket_data["apply_infos"]``，为每个 apply_info 产出一个 ResourceGroup
      - 每组固定 1 个 RevokeUnit（single 机器承载 M 个 Single 集群实例）
      - 端口按 ``start_mysql_port + i`` 展开，i ∈ range(min(inst_num, len(clusters)))
      - 域名列表仅含 ``clusters[*].master``（Single 架构无 slave 域名）

    使用方式：
      extractor = MysqlSingleApplyExtractor()
      groups = extractor.extract(ticket_data)

    线程安全：是（无实例状态）
    边界：
      - ticket_data 类型非 dict / 关键字段（apply_infos / start_mysql_port /
        inst_num / bk_biz_id）缺失或类型非法 -> 抛 :class:`NormalTenDBFlowException`
      - 单个 apply_info 缺关键字段（new_ip / clusters）或 actual_inst_count <= 0
        -> 抛 :class:`NormalTenDBFlowException`
      - 异常一律由上层 ``revoke_flow`` 顶层 try/except 统一兜底，本类不做局部吞异常
    """

    def extract(self, ticket_data: Dict) -> List[ResourceGroup]:
        """从 TenDBSingle 部署单据 ticket_data 提取候选组列表。

        :param ticket_data: MYSQL_SINGLE_APPLY 单据的 flow ticket_data
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

        start_mysql_port = ticket_data.get("start_mysql_port")
        inst_num = ticket_data.get("inst_num")
        bk_biz_id = ticket_data.get("bk_biz_id")

        # 类型规整（ticket_data 里可能是字符串）
        try:
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
        start_mysql_port: int,
        inst_num: int,
        bk_biz_id: int,
        clb_regions: Tuple[str, ...],
    ) -> ResourceGroup:
        """处理一个 apply_info，产出 ResourceGroup。

        :param apply_info: 单个 apply_info 字典，形如 {"new_ip": {...}, "clusters": [...]}
        :param apply_info_idx: apply_info 在 apply_infos 中的索引，用于组 group_id 构造
        :param start_mysql_port: ticket_data.start_mysql_port
        :param inst_num: ticket_data.inst_num
        :param bk_biz_id: 业务 id
        :return: :class:`ResourceGroup`
        边界：
          - apply_info 类型非 dict -> 抛 :class:`NormalTenDBFlowException`
          - new_ip 非 dict 或缺 ip/bk_host_id -> 抛 :class:`NormalTenDBFlowException`
          - clusters 非 list 或空 -> 抛 :class:`NormalTenDBFlowException`
          - actual_inst_count <= 0 -> 抛 :class:`NormalTenDBFlowException`
          - RevokeUnit 构造字段类型非法 -> 抛 :class:`NormalTenDBFlowException`
        """
        if not isinstance(apply_info, dict):
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}] is not dict: {!r}".format(_ERR_PREFIX, apply_info_idx, apply_info)
            )

        new_ip = apply_info.get("new_ip")
        clusters = apply_info.get("clusters") or []

        if not isinstance(new_ip, dict) or "ip" not in new_ip or "bk_host_id" not in new_ip:
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}].new_ip missing ip/bk_host_id: {!r}".format(
                    _ERR_PREFIX, apply_info_idx, new_ip
                )
            )
        if not isinstance(clusters, list) or not clusters:
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}].clusters empty or non-list".format(_ERR_PREFIX, apply_info_idx)
            )

        # 计算实际部署端口数量（与 mysql_single_apply_flow.py 的 __calc_install_ports 完全对齐）
        actual_inst_count: int = min(inst_num, len(clusters))
        if actual_inst_count <= 0:
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}] actual_inst_count <= 0 (inst_num={} clusters={})".format(
                    _ERR_PREFIX, apply_info_idx, inst_num, len(clusters)
                )
            )

        mysql_ports: Tuple[int, ...] = tuple(start_mysql_port + i for i in range(actual_inst_count))

        # 提取集群主域名列表（Single 架构只绑主域名，无 slave 域名）
        cluster_domains: Tuple[str, ...] = tuple(
            c["master"] for c in clusters if isinstance(c, dict) and c.get("master")
        )

        # ---- 构造组内 units ----
        # TenDBSingle 一组只有 1 台机器（single 单节点，无 proxy、无 slave）
        try:
            unit = RevokeUnit(
                ip=str(new_ip["ip"]),
                bk_host_id=int(new_ip["bk_host_id"]),
                bk_cloud_id=int(new_ip.get("bk_cloud_id", 0)),
                bk_biz_id=bk_biz_id,
                role=InstanceRole.ORPHAN.value,
                expected_ports=mysql_ports,
                cluster_type=ClusterType.TenDBSingle.value,
            )
        except (TypeError, ValueError) as err:
            raise NormalTenDBFlowException(
                message="{} apply_infos[{}].new_ip field types illegal: {}".format(_ERR_PREFIX, apply_info_idx, err)
            )

        return ResourceGroup(
            group_id="apply_info_{}".format(apply_info_idx),
            units=(unit,),
            cluster_domains=cluster_domains,
            clb_regions=clb_regions,
        )
