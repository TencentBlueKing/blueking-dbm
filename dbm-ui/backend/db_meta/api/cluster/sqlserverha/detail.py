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

from backend.db_meta.api.cluster.base.graph import Graphic, Group, LineLabel
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster


def scan_cluster(cluster: Cluster) -> Graphic:
    """
    所有往 error report 中添加的信息都是集群的检查规则
    这部分应该抽象出去独立生成 report
    """
    graph = Graphic(node_id=Graphic.generate_graphic_id(cluster))

    # 获得master节点组
    masters, master_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.BACKEND_MASTER, group_name=_("Master 节点")
    )
    # 获得主访问入口
    master_entry = masters.first().bind_entry.first()
    master_entry_group = Group(node_id="master_bind_entry_group", group_name=_("访问入口（主）"))
    graph.add_node(master_entry, to_group=master_entry_group)
    # 主访问入口 --> master
    graph.add_line(source=master_entry_group, target=master_group, label=LineLabel.Access)

    # 获得slave节点组
    slaves, slave_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.BACKEND_SLAVE, group_name=_("Slave 节点")
    )
    # 获得从访问入口
    slave_entry = masters.first().bind_entry.first()
    slave_entry_group = Group(node_id="slave_bind_entry_group", group_name=_("访问入口（从）"))
    graph.add_node(slave_entry, to_group=slave_group)
    # 从访问入口 --> slave
    graph.add_line(source=slave_entry_group, target=slave_group, label=LineLabel.Access)

    # master ---> slave
    graph.add_line(source=master_group, target=slave_group, label=LineLabel.Rep)

    return graph
