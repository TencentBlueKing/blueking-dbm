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
    redis主从关系拓扑图
    """
    graph = Graphic(node_id=Graphic.generate_graphic_id(cluster))

    # 获取master节点组
    master_insts, master_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.REDIS_MASTER, group_name=_("Master 节点")
    )

    # 获取slave节点组
    slave_insts, slave_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.REDIS_SLAVE, group_name=_("Slave 节点")
    )

    # 获得访问入口节点组
    entry = master_insts.first().bind_entry.first()
    __, entry_group = graph.add_node(entry)

    # 访问入口 ---> Master/Slave节点，关系为：绑定
    graph.add_line(source=entry_group, target=master_group, label=LineLabel.Bind)
    # Master ---> Slave, 关系为同步
    graph.add_line(source=master_group, target=slave_group, label=LineLabel.Rep)

    return graph
