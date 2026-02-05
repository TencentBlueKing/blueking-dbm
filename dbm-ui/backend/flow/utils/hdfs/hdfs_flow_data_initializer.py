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
import copy
import logging.config
from typing import Any, Dict

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName, ReqType
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import HdfsRoleEnum, LevelInfoEnum, NameSpaceEnum

logger = logging.getLogger("flow")


class HdfsFlowDataInitializer:
    """
    HDFS流程数据初始化工具类
    集中管理HDFS流程的数据初始化逻辑，避免代码重复
    """

    @classmethod
    def init_apply_data(cls, ticket_data: dict) -> Dict[str, Any]:
        """初始化集群申请流程数据

        Args:
            ticket_data: 单据数据

        Returns:
            初始化后的data字典
        """
        data = copy.deepcopy(ticket_data)
        data["nn_domain"] = build_nn_domain_mapping(ticket_data)
        return data

    @classmethod
    def init_destroy_data(cls, ticket_data: dict) -> Dict[str, Any]:
        """初始化集群销毁/禁用流程数据

        仿照Doris的get_flow_base_data方法，从cluster_id获取集群信息

        Args:
            ticket_data: 单据数据，必须包含cluster_id

        Returns:
            初始化后的data字典，包含集群的基本信息
        """
        data = copy.deepcopy(ticket_data)

        # 从cluster_id获取cluster对象
        cluster = Cluster.objects.get(id=ticket_data["cluster_id"])

        # 填充集群基本信息，将cluster对象的属性填充到data字典中，key与部署单据保持一致
        data["cluster_phase"] = cluster.phase
        data["cluster_name"] = cluster.name
        data["domain"] = cluster.immute_domain
        data["db_version"] = cluster.major_version
        data["bk_biz_id"] = cluster.bk_biz_id
        data["bk_cloud_id"] = cluster.bk_cloud_id

        # 从dbconfig获取配置信息
        dbconfig = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": LevelName.CLUSTER,
                "level_value": cluster.immute_domain,
                "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
                "conf_file": cluster.major_version,
                "conf_type": ConfType.DBCONF,
                "namespace": NameSpaceEnum.Hdfs,
                "format": FormatType.MAP_LEVEL,
                "method": ReqType.GENERATE_AND_PUBLISH,
            }
        )
        hdfs_config = dbconfig["content"]
        # 从dbconfig获取集群配置的端口信息
        data["rpc_port"] = hdfs_config["rpc_port"]
        data["http_port"] = hdfs_config["http_port"]
        return data

    @classmethod
    def init_scale_up_data(cls, root_id: str, ticket_data: dict) -> Dict[str, Any]:
        """初始化扩容流程数据

        Args:
            root_id: 流程根ID
            ticket_data: 单据数据

        Returns:
            初始化后的data字典
        """
        data = cls.init_apply_data(root_id, ticket_data)

        return data


def get_node_ips_in_ticket_by_role(data: dict, role: str) -> list:
    if role == HdfsRoleEnum.JournalNode.value:
        return get_node_ips_in_ticket_by_role(data, HdfsRoleEnum.ZooKeeper.value)

    # 适配当前HDFS替换单据没有nodes字段
    nodes = data.get("nodes")
    if not nodes or role not in nodes:
        return []

    return [node["ip"] for node in nodes[role]]


def get_all_node_ips_in_ticket(data: dict) -> list:
    """
    获取单据中所有节点的IP列表
    由于ZooKeeper 和 NameNode 可能是相同的节点，所以需要去重
    """
    ips = set()
    for role in data.get("nodes", {}):
        role_ips = get_node_ips_in_ticket_by_role(data, role)
        ips.update(role_ips)
    return list(ips)


# 从dbmeta获取集群所有节点的IP列表
def get_all_node_ips_in_dbmeta(cluster_id: int) -> list:
    cluster = Cluster.objects.get(id=cluster_id)
    storage_ips = list(set(StorageInstance.objects.filter(cluster=cluster).values_list("machine__ip", flat=True)))
    return storage_ips


def get_webui_ip(data: dict) -> str:
    """
    获取HAProxy安装IP
    选择逻辑：单据里不在NameNode角色，只在Zookeeper角色里的任意一个ip

    Args:
        data: 单据数据

    Returns:
        HAProxy安装IP
    """
    # 获取Zookeeper角色IP列表
    zk_ips = get_node_ips_in_ticket_by_role(data, HdfsRoleEnum.ZooKeeper.value)
    # 获取NameNode角色IP列表
    nn_ips = get_node_ips_in_ticket_by_role(data, HdfsRoleEnum.NameNode.value)

    # 从Zookeeper IP中排除NameNode IP，选择第一个可用的IP
    available_zk_ips = [ip for ip in zk_ips if ip not in nn_ips]
    if available_zk_ips:
        return available_zk_ips[0]
    else:
        # 如果没有可用的Zookeeper IP，使用第一个Zookeeper IP作为备选
        return zk_ips[0]


def build_nn_domain_mapping(ticket_data: dict) -> Dict[str, str]:
    """
    构建 NameNode IP 到域名的映射
    返回格式: {nn1_ip: "nn1.domain", nn2_ip: "nn2.domain"}
    """
    nn_domain = {}
    nn_ips = get_node_ips_in_ticket_by_role(ticket_data, HdfsRoleEnum.NameNode.value)
    domain = ticket_data.get("domain", "")
    if len(nn_ips) > 0 and domain:
        nn_domain[nn_ips[0]] = f"nn1.{domain}"
    if len(nn_ips) > 1 and domain:
        nn_domain[nn_ips[1]] = f"nn2.{domain}"
    return nn_domain
