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

from django.utils.translation import gettext as _

from backend.db_meta.api.cluster.base.graph import Graphic, Group, LineLabel, Node
from backend.db_meta.api.cluster.tendbcluster.handler import TenDBClusterClusterHandler
from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster


def scan_cluster(cluster: Cluster) -> Graphic:
    """
    绘制spider的拓扑结构图
    """

    def build_spider_entry_relations(role, spider_group_name, entry_group_id, entry_group_name):
        """获得Spider和对应的访问入口，并建立访问关系"""

        spider_insts, spider_group = graph.add_spider_nodes(cluster, role, group_name=spider_group_name)
        if not spider_insts:
            return spider_insts, spider_group

        spider_entry = spider_insts.first().bind_entry.first()
        spider_entry_group = Group(node_id=entry_group_id, group_name=entry_group_name)
        __, spider_entry_group = graph.add_node(spider_entry, to_group=spider_entry_group)

        graph.add_line(source=spider_entry_group, target=spider_group, label=LineLabel.Access)

        return spider_insts, spider_group

    def _get_or_create_group(instances, group_name):
        """辅助函数：创建或获取组"""
        if not instances:
            raise ValueError(f"No instances provided for group {group_name}.")
        return graph.get_or_create_group(group_id=Node.generate_node_type(instances[0]), group_name=group_name)

    def _add_nodes_to_group(instances, group):
        """辅助函数：将实例添加到组中"""
        for inst in instances:
            graph.add_node(inst, group)

    def add_remote_nodes(cluster):
        """获取remote节点，并跟相应的spider建立关系"""
        remote_db, remote_dr = TenDBClusterClusterHandler.get_remote_infos(cluster.storages)
        # 创建或获取 RemoteDB 和 RemoteDR 组
        db_group = _get_or_create_group(remote_db, "RemoteDB")
        dr_group = _get_or_create_group(remote_dr, "RemoteDR")

        # 将实例添加到相应的组中
        _add_nodes_to_group(remote_db, db_group)
        _add_nodes_to_group(remote_dr, dr_group)

        return db_group, dr_group

    graph = Graphic(node_id=Graphic.generate_graphic_id(cluster))

    # 建立spider master和访问入口（主）的关系
    spider_master_insts, spider_master_group = build_spider_entry_relations(
        TenDBClusterSpiderRole.SPIDER_MASTER,
        spider_group_name=_("Spider Master"),
        entry_group_id=_("spider_master_entry_bind"),
        entry_group_name=_("访问入口（主）"),
    )
    # 建立spider slave和访问入口（从）的关系
    __, spider_slave_group = build_spider_entry_relations(
        TenDBClusterSpiderRole.SPIDER_SLAVE,
        spider_group_name=_("Spider Slave"),
        entry_group_id=_("spider_slave_entry_bind"),
        entry_group_name=_("访问入口（从）"),
    )

    # 建立spider_master和spider_slave之间的关系
    if spider_master_group and spider_slave_group:
        graph.add_line(source=spider_master_group, target=spider_slave_group, label=LineLabel.Access)

    # 按master/slave组分片数排序
    remote_db_group, remote_dr_group = add_remote_nodes(cluster)

    # 建立spider_master和remote db的关系
    if spider_master_group:
        graph.add_line(source=spider_master_group, target=remote_db_group, label=LineLabel.Access)

    # 建立spider_master和remote dr的关系
    if spider_slave_group:
        graph.add_line(source=spider_master_group, target=remote_dr_group, label=LineLabel.Access)

    # 建立remote dr与remote db的数据同步关系
    graph.add_line(source=remote_db_group, target=remote_dr_group, label=LineLabel.Rep)

    # 收纳运维节点
    spider_mnt_insts, spider_mnt_group = graph.add_spider_nodes(
        cluster, TenDBClusterSpiderRole.SPIDER_MNT, group_name=_("Spider 运维节点")
    )
    if spider_mnt_insts:
        graph.add_line(source=spider_mnt_group, target=remote_db_group, label=LineLabel.Access)

    # 收纳中控节点 TODO: 如何表示关系
    controller_group = Group(node_id=_("controller_group"), group_name=_("中控节点"))
    graph.groups.append(controller_group)
    for inst in spider_master_insts:
        node = Node(inst, node_id=f"{inst.machine.ip}:{inst.admin_port}", node_type="controller_node")
        controller_group.add_child(node)
        graph.nodes.append(node)

    return graph
