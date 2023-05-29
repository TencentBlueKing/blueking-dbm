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

from backend.db_meta.api.cluster.base.graph import Graphic, LineLabel
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster


def scan_cluster(cluster: Cluster) -> Graphic:
    """
    绘制es的拓扑结构图
    """
    graph = Graphic(node_id=Graphic.generate_graphic_id(cluster))

    # 获得Client节点组
    client_insts, client_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.ES_CLIENT, group_name=_("Client 节点")
    )

    # 获得Master节点组，冷节点组，热节点组
    _dummy, master_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.ES_MASTER, group_name=_("Master 节点")
    )
    _dummy, hot_node_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.ES_DATANODE_HOT, group_name=_("热节点")
    )
    _dummy, cold_node_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.ES_DATANODE_COLD, group_name=_("冷节点")
    )

    # 获得访问入口节点组
    entry = client_insts.first().bind_entry.first()
    _dummy, entry_group = graph.add_node(entry)

    # 访问入口 ---> Client节点，关系为：访问
    graph.add_line(source=entry_group, target=client_group, label=LineLabel.Access)

    # Client节点 ---> Master/冷/热节点，关系为：访问
    graph.add_line(source=client_group, target=master_group, label=LineLabel.Access)
    graph.add_line(source=client_group, target=hot_node_group, label=LineLabel.Access)
    graph.add_line(source=client_group, target=cold_node_group, label=LineLabel.Access)

    return graph
