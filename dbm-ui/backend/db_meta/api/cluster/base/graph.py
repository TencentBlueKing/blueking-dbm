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

import operator
from dataclasses import asdict, dataclass, field
from functools import reduce
from typing import Dict, List, Optional, Tuple, Union

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceRole, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance, StorageInstance
from blue_krill.data_types.enum import EnumField, StructuredEnum


@dataclass
class Node:
    node_id: str
    node_type: str
    url: str
    status: str

    @staticmethod
    def generate_node_id(ins: Union[StorageInstance, ProxyInstance, ClusterEntry]) -> str:
        if isinstance(ins, ClusterEntry):
            return ins.entry
        return "{}:{}".format(ins.machine.ip, ins.port)

    @staticmethod
    def generate_node_type(ins: Union[StorageInstance, ProxyInstance, ClusterEntry]) -> str:
        if isinstance(ins, StorageInstance):
            return "{}::{}".format(ins.machine_type, ins.instance_role)
        elif isinstance(ins, ProxyInstance):
            # 如果具有tendbclusterspiderext，则认为该Proxy是Spider
            if hasattr(ins, "tendbclusterspiderext"):
                return ins.tendbclusterspiderext.spider_role
            return ins.machine_type
        else:
            return "entry_{}".format(ins.cluster_entry_type)

    @staticmethod
    def generate_url(ins: Union[StorageInstance, ProxyInstance, ClusterEntry]) -> str:
        if isinstance(ins, (StorageInstance, ProxyInstance)):
            if ins.cluster_type == ClusterType.TenDBCluster:
                url_tpl = (
                    "/database/{bk_biz_id}/spider-manage/list-instance?"
                    "instance_address={ip}:{port}&cluster_id={cluster_id}"
                )
            else:
                url_tpl = (
                    "/database/{bk_biz_id}/{cluster_type}-instance?"
                    "instance_address={ip}:{port}&cluster_id={cluster_id}"
                )
            # url 跳转到实例详情
            return url_tpl.format(
                bk_biz_id=ins.bk_biz_id,
                cluster_type=ins.cluster_type,
                cluster_id=ins.cluster.first().id,
                ip=ins.machine.ip,
                port=ins.port,
            )
        if isinstance(ins, ClusterEntry):
            # ClusterEntry 需考虑 北极星、CLB 等访问方式等跳转
            if ins.cluster_entry_type == ClusterEntryType.POLARIS:
                return "{polaris_url}/#/services/info/detail/Production/{polaris_service_name}".format(
                    polaris_url=env.POLARIS_URL, polaris_service_name=ins.entry
                )

        return ""

    @staticmethod
    def generate_status(ins: Union[StorageInstance, ProxyInstance, ClusterEntry]) -> str:
        if isinstance(ins, (StorageInstance, ProxyInstance)):
            return ins.status
        else:
            return ins.cluster.status

    def __init__(
        self,
        ins: Union[StorageInstance, ProxyInstance, ClusterEntry],
        node_id: str = None,
        node_type: str = None,
        url: str = None,
        status: str = None,
    ):
        self.node_id = node_id or Node.generate_node_id(ins)
        self.node_type = node_type or Node.generate_node_type(ins)
        self.url = url or Node.generate_url(ins)
        self.status = status or Node.generate_status(ins)
        super(Node, self).__init__()


@dataclass
class Group:
    node_id: str
    group_name: str = field(default="")
    children_id: List[str] = field(init=False)

    def __post_init__(self):
        self.group_name = getattr(self, "group_name", self.node_id)
        self.children_id = []

    @staticmethod
    def generate_group_info(ins: Union[StorageInstance, ProxyInstance, ClusterEntry]) -> Tuple[str, str]:
        """
        :returns:
            Tuple(group_id, group_name)
        """
        # 默认 group_id 和 group_name 都使用统一的规则生成
        node_id = group_name = Node.generate_node_type(ins)
        # 以下情况，则对 group_name 进行特殊赋值
        if isinstance(ins, StorageInstance):
            group_name = ins.instance_inner_role.capitalize()
        elif isinstance(ins, ProxyInstance):
            group_name = ins.machine_type.capitalize()
        elif isinstance(ins, ClusterEntry):
            group_name = _("访问入口")

        return node_id, group_name

    def add_child(self, node: Node):
        if node.node_id not in self.children_id:
            self.children_id.append(node.node_id)


class LineEndpointType(StructuredEnum):
    Node = EnumField("node", _("node"))
    Group = EnumField("group", _("group"))


class LineLabel(StructuredEnum):
    Rep = EnumField("rep", _("同步"))
    Access = EnumField("access", _("访问"))
    Bind = EnumField("bind", _("域名绑定"))
    ReadWrite = EnumField("readwrite", _("读写"))


@dataclass
class Line:
    source: str
    source_type: str
    target: str
    target_type: str
    label: str
    label_name: str = field(init=False)

    def __init__(self, source: Union[Node, Group], target: Union[Node, Group], label: LineLabel):
        self.source = source.node_id
        self.target = target.node_id
        self.label = label.value
        self.label_name = label.get_choice_label(label.value)

        if isinstance(source, Node):
            self.source_type = LineEndpointType.Node.value
        else:
            self.source_type = LineEndpointType.Group.value

        if isinstance(target, Node):
            self.target_type = LineEndpointType.Node.value
        else:
            self.target_type = LineEndpointType.Group.value

        super(Line, self).__init__()


class ForeignRelationType(StructuredEnum):
    RepTo = EnumField("rep_to", _("同步到其他集群"))
    RepFrom = EnumField("rep_from", _("从其他集群同步"))
    AccessTo = EnumField("access_to", _("访问其他集群"))
    AccessFrom = EnumField("access_from", _("从其他集群访问"))


@dataclass
class Graphic:
    node_id: str
    nodes: List[Node] = field(init=False)
    groups: List[Group] = field(init=False)
    lines: List[Line] = field(init=False)
    foreign_relations: Dict[str, List[Dict]] = field(init=False)

    # error_report: List[str] = field(init=False)

    def __post_init__(self):
        self.nodes = []
        self.groups = []
        self.lines = []
        self.foreign_relations = {}
        # self.error_report = []

        for e in ForeignRelationType.get_values():
            self.foreign_relations[e] = []

    @staticmethod
    def generate_graphic_id(cluster: Cluster) -> str:
        return cluster.immute_domain

    def add_node(
        self, ins: Union[StorageInstance, ProxyInstance, ClusterEntry], to_group: Optional[Group] = None
    ) -> (Node, Group):
        if to_group:
            node_grp = self.get_or_create_group(to_group.node_id, to_group.group_name)
        else:
            node_grp = self.get_or_create_group(*Group.generate_group_info(ins))

        node = Node(ins)
        if node in self.nodes:
            return node, to_group

        node_grp.add_child(node)
        self.nodes.append(node)
        return node, node_grp

    def add_instance_nodes(
        self, cluster: Cluster, roles: Union[InstanceRole, List[InstanceRole]], group_name: str
    ) -> (StorageInstance, Group):
        """
        批量添加StorageInstance实例节点，实例节点满足在同一group中
        TODO: 目前这个函数主要为大数据拓扑结构，暂时不会用到ProxyInstance，后续可拓展
        """
        if isinstance(roles, InstanceRole):
            roles = [roles]

        instances = StorageInstance.objects.filter(
            reduce(operator.or_, [Q(instance_role=role) for role in roles]), cluster=cluster
        )
        if not instances:
            return None, None

        group = self.get_or_create_group(group_id=Node.generate_node_type(instances.first()), group_name=group_name)
        for inst in instances:
            self.add_node(inst, group)

        return instances, group

    def add_spider_nodes(
        self, cluster: Cluster, role: TenDBClusterSpiderRole, group_name: str
    ) -> (StorageInstance, Group):
        """
        批量添加spider节点
        """
        spider_nodes = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=role)
        if not spider_nodes:
            return None, None

        group = self.get_or_create_group(group_id=Node.generate_node_type(spider_nodes.first()), group_name=group_name)
        for inst in spider_nodes:
            self.add_node(inst, group)

        return spider_nodes, group

    def add_instance_nodes_with_machinetype(
        self,
        cluster: Cluster,
        roles: Union[InstanceRole, List[InstanceRole]],
        machine_type: MachineType,
        group_name: str,
    ) -> (StorageInstance, Group):
        """
        批量添加StorageInstance实例节点，实例节点满足在同一group中
        适用于 Mongo 架构
        """
        if isinstance(roles, InstanceRole):
            roles = [roles]

        instances = StorageInstance.objects.filter(
            reduce(operator.or_, [Q(instance_role=role) for role in roles]), cluster=cluster, machine_type=machine_type
        )
        group = self.get_or_create_group(group_id=Node.generate_node_type(instances.first()), group_name=group_name)
        for inst in instances:
            self.add_node(inst, group)

        return instances, group

    def add_foreign_cluster(self, relate_type: ForeignRelationType, cluster: Cluster):
        """
        这里的东西需要有足够的信息当作参数调用 detail
        """

        if cluster.immute_domain not in [
            fr["immute_domain"] for fr in self.foreign_relations[relate_type.value]
        ]:  # self.foreign_relations[relate_type.value]:
            self.foreign_relations[relate_type.value].append(
                {
                    "immute_domain": cluster.immute_domain,
                    "bk_biz_id": cluster.bk_biz_id,
                    "db_module_id": cluster.db_module_id,
                    "name": cluster.name,
                }
            )

    def get_or_create_group(self, group_id: str, group_name: str = "") -> Group:
        for grp in self.groups:
            if group_id == grp.node_id:
                return grp

        grp = Group(group_id, group_name)
        self.groups.append(grp)
        return grp

    def add_line(self, source: Union[Node, Group], target: Union[Node, Group], label: LineLabel):
        ln = Line(source=source, target=target, label=label)
        if ln not in self.lines:
            self.lines.append(ln)

    def to_dict(self):
        return asdict(self)
