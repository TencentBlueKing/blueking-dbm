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
from collections import defaultdict
from typing import Any, Dict, Tuple

from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName, ReqType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import HdfsRoleEnum, LevelInfoEnum, NameSpaceEnum, UserName
from backend.flow.engine.bamboo.scene.hdfs.exceptions import (
    AuthInfoNullException,
    HaProxyHostNullException,
    ReplaceMachineCountException,
    ReplaceMachineNullException,
)
from backend.flow.utils.base.payload_handler import PayloadHandler

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
        return cls._init_cluster_data(ticket_data)[0]

    @classmethod
    def init_scale_up_data(cls, ticket_data: dict) -> Dict[str, Any]:
        """初始化扩容流程数据。本次上架的 DN 仍在单据 nodes 里，用到时再取。"""
        return cls._init_dn_change_data(ticket_data)

    @classmethod
    def init_shrink_data(cls, ticket_data: dict) -> Dict[str, Any]:
        """初始化缩容流程数据。本次下架的 DN 仍在单据 nodes 里，用到时再取。"""
        return cls._init_dn_change_data(ticket_data)

    @classmethod
    def init_replace_data(cls, ticket_data: dict) -> Dict[str, Any]:
        """初始化 DN 替换流程数据。新旧 DN 留在 new_nodes、old_nodes，由两段子流程分别放进 nodes。"""
        old_dn_ips = get_node_ips_in_ticket_by_role(
            {"nodes": ticket_data.get("old_nodes", {})}, HdfsRoleEnum.DataNode.value
        )
        new_dn_ips = get_node_ips_in_ticket_by_role(
            {"nodes": ticket_data.get("new_nodes", {})}, HdfsRoleEnum.DataNode.value
        )
        if not old_dn_ips:
            logger.error(_("没有需要替换的角色IP"))
            raise ReplaceMachineNullException()
        if len(old_dn_ips) != len(new_dn_ips):
            logger.error(_("替换HDFS DataNode角色IP不一致"))
            raise ReplaceMachineCountException(hdfs_role=HdfsRoleEnum.DataNode)

        data = cls._init_dn_change_data(ticket_data)
        data["ip_source"] = IpSource.MANUAL_INPUT
        return data

    @classmethod
    def _init_dn_change_data(cls, ticket_data: dict) -> Dict[str, Any]:
        """扩缩容、替换共用：集群基础信息、存量角色 IP、NameNode 主机映射、include/exclude 路径和账号"""
        data, cluster, hdfs_config = cls._init_cluster_data(ticket_data)

        role_ips = defaultdict(list)
        for role, ip in StorageInstance.objects.filter(cluster=cluster).values_list("instance_role", "machine__ip"):
            role_ips[role].append(ip)
        data["nn_ips"] = role_ips[InstanceRole.HDFS_NAME_NODE.value]
        data["zk_ips"] = role_ips[InstanceRole.HDFS_ZOOKEEPER.value]
        data["jn_ips"] = role_ips[InstanceRole.HDFS_JOURNAL_NODE.value]
        data["dn_ips"] = role_ips[InstanceRole.HDFS_DATA_NODE.value]

        data["nn1_ip"] = hdfs_config["nn1_ip"]
        data["nn2_ip"] = hdfs_config["nn2_ip"]
        # 只保留 NameNode 域名。DN 不写入 host_map，渲染时用本机 IP 替换 {{dn_host}}
        data["all_ip_hosts"] = {data["nn1_ip"]: hdfs_config["nn1_host"], data["nn2_ip"]: hdfs_config["nn2_host"]}
        data["dfs_include_file"] = hdfs_config["hdfs-site"]["dfs.hosts"]
        data["dfs_exclude_file"] = hdfs_config["hdfs-site"]["dfs.hosts.exclude"]

        password = PayloadHandler.get_bigdata_password_by_cluster(cluster, 0, UserName.HDFS_DEFAULT)
        if password:
            data["username"] = UserName.HDFS_DEFAULT
            data["password"] = password
        else:
            logger.error("cannot get auth info from password service")
            data["username"] = hdfs_config.get("username", "")
            data["password"] = hdfs_config.get("password", "")
        # 密码服务和 dbconfig 都拿不到账号时直接失败，避免把空账号继续传给后续步骤
        if not data["username"] or not data["password"]:
            raise AuthInfoNullException()
        return data

    @classmethod
    def _init_cluster_data(cls, ticket_data: dict) -> Tuple[Dict[str, Any], Cluster, Dict[str, Any]]:
        """按 cluster_id 填充集群基础信息，同时返回集群对象和集群级配置供调用方继续取值"""
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
        data["rpc_port"] = int(hdfs_config["rpc_port"])
        data["http_port"] = int(hdfs_config["http_port"])
        return data, cluster, hdfs_config


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


def get_haproxy_ips(data: dict) -> list:
    """获取 HAProxy 安装 IP，也是主域名映射的 IP：不与 NameNode 同机的全部 ZooKeeper。"""
    zk_ips = get_node_ips_in_ticket_by_role(data, HdfsRoleEnum.ZooKeeper.value)
    nn_ips = set(get_node_ips_in_ticket_by_role(data, HdfsRoleEnum.NameNode.value))
    return [ip for ip in zk_ips if ip not in nn_ips]


def get_webui_ip(data: dict) -> str:
    """获取写入 extension 表的 HAProxy 管理 IP，取 HAProxy 安装列表中的第一台。"""
    haproxy_ips = get_haproxy_ips(data)
    # 正常集群 ZK 3 台、NN 2 台，一定存在与 NN 不同机的 ZK；为空说明单据/集群数据异常，直接报错
    if not haproxy_ips:
        raise HaProxyHostNullException()
    return haproxy_ips[0]


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
