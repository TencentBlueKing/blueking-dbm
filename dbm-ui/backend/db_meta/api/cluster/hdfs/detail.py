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
    绘制hdfs的拓扑结构图
    """
    graph = Graphic(node_id=Graphic.generate_graphic_id(cluster))

    # 获得NameNode节点组，DataNode节点组，Zookeeper节点组和JournalNode节点组
    _dummy, nn_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.HDFS_NAME_NODE, group_name=_("NameNode 节点")
    )
    dn_insts, dn_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.HDFS_DATA_NODE, group_name=_("DataNode 节点")
    )
    _dummy, zk_group = graph.add_instance_nodes(
        cluster=cluster,
        roles=InstanceRole.HDFS_ZOOKEEPER,
        group_name=_("Zookeeper 节点"),
    )
    _dummy, jn_group = graph.add_instance_nodes(
        cluster=cluster,
        roles=InstanceRole.HDFS_JOURNAL_NODE,
        group_name=_("Journal 节点"),
    )

    # 获得访问入口节点组
    entry = dn_insts.first().bind_entry.first()
    _dummy, entry_group = graph.add_node(entry)

    # 访问入口 ---> NameNode节点，关系为：访问
    graph.add_line(source=entry_group, target=nn_group, label=LineLabel.Access)

    # NameNode节点 ---> ZK节点组, 关系为：读写
    graph.add_line(source=nn_group, target=zk_group, label=LineLabel.ReadWrite)

    # NameNode节点 ---> JN节点组, 关系为：读写
    graph.add_line(source=nn_group, target=jn_group, label=LineLabel.ReadWrite)

    # NameNode节点 <---> DataNode节点，关系为：访问
    graph.add_line(source=nn_group, target=dn_group, label=LineLabel.Access)
    graph.add_line(source=dn_group, target=nn_group, label=LineLabel.Access)

    return graph
