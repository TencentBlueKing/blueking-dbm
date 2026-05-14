# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Dict, List, Optional, Tuple

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException


def resolve_sqlserver_addresses(
    cluster_domain: str,
    address: Optional[str] = None,
    default_role: str = "all",
) -> Tuple[int, List[Dict]]:
    """根据集群域名解析出待访问的 sqlserver 实例列表。

    用于把 mcp 工具的入参（cluster_domain + 可选 address）转换为
    实际下发 rpc 所需的 (bk_cloud_id, [{address, role, is_stand_by}, ...])。

    :param cluster_domain: 集群不可变域名 (immute_domain)
    :param address: 用户显式指定的实例地址 "ip:port"，可选
    :param default_role: 当 address 为空时的默认选择策略：
        - "all"    : 返回集群内所有 storage 实例（用于"实例基础信息查询"场景）
        - "master" : 仅返回 master 实例（用于"性能/阻塞/执行计划"场景）
    :return: (bk_cloud_id, instances)
        instances 元素结构: {"address": "ip:port", "role": "<inner_role>", "is_stand_by": bool}
    """
    cluster = Cluster.objects.get(immute_domain=cluster_domain)
    bk_cloud_id = cluster.bk_cloud_id

    # 集群内全部 storage 实例的元信息
    all_instances: List[Dict] = [
        {
            "address": s.ip_port,
            "role": s.instance_inner_role,
            "is_stand_by": s.is_stand_by,
        }
        for s in cluster.storageinstance_set.all()
    ]

    if not all_instances:
        raise DBMMcpBaseException(msg=f"cluster {cluster_domain} has no storage instances")

    # 用户显式指定 address：必须属于该集群
    if address:
        matched = [item for item in all_instances if item["address"] == address]
        if not matched:
            raise DBMMcpBaseException(msg=f"address {address} does not belong to cluster {cluster_domain}")
        return bk_cloud_id, matched

    # 未指定 address，按 default_role 决定缺省行为
    if default_role == "all":
        return bk_cloud_id, all_instances

    # 这里要兼容单节点集群的情况
    if default_role == "master":
        masters = [
            item for item in all_instances if item["role"] in [InstanceInnerRole.MASTER, InstanceInnerRole.ORPHAN]
        ]
        if not masters:
            raise DBMMcpBaseException(msg=f"cluster {cluster_domain} has no master instance")
        return bk_cloud_id, masters[:1]

    raise DBMMcpBaseException(msg=f"invalid default_role: {default_role}")


def resolve_target_instance(cluster_domain: str, address: Optional[str]) -> Tuple[int, Dict]:
    """resolve_sqlserver_addresses 的"单实例"便捷封装。

    场景：按表 / 按业务库分析的工具（index_analysis、list_table_status 等）
          只关心单一目标实例，缺省走 master。

    :return: (bk_cloud_id, instance_info)
        instance_info 结构: {"address": "ip:port", "role": "...", "is_stand_by": bool}
    """
    bk_cloud_id, instances = resolve_sqlserver_addresses(
        cluster_domain=cluster_domain, address=address, default_role="master"
    )
    return bk_cloud_id, instances[0]
