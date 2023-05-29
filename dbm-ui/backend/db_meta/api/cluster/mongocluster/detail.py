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
from backend.db_meta.enums import InstanceRole, MachineType
from backend.db_meta.models import Cluster


def scan_cluster(cluster: Cluster) -> Graphic:
    """
    绘制Mongo Sharded Cluster 的拓扑结构图
    mongos                             Shard-1:Primary Shard-1:Secondary  Shard-1:Backup
    mongos                             Shard-2:Primary Shard-2:Secondary  Shard-2:Backup
    mongos                             Shard-3:Primary Shard-3:Secondary  Shard-3:Backup
    mongos           configServer      Shard-4:Primary Shard-4:Secondary  Shard-4:Backup
    mongos           configServer      Shard-5:Primary Shard-5:Secondary  Shard-5:Backup
    mongos           configServer      Shard-6:Primary Shard-6:Secondary  Shard-6:Backup
    mongos                             Shard-7:Primary Shard-7:Secondary  Shard-7:Backup
    mongos                             Shard-8:Primary Shard-8:Secondary  Shard-8:Backup
    mongos                             Shard-9:Primary Shard-9:Secondary  Shard-9:Backup
    """
    graph = Graphic(node_id=Graphic.generate_graphic_id(cluster))

    mongos_insts, mongos_group = graph.add_instance_nodes(
        cluster=cluster, roles=InstanceRole.MONOGOS, group_name=_("Mongos 节点")
    )
    _dummy, configs_group = graph.add_instance_nodes_with_machinetype(
        cluster=cluster,
        roles=[
            InstanceRole.MONGO_M1,
            InstanceRole.MONGO_M2,
            InstanceRole.MONGO_M3,
            InstanceRole.MONGO_M4,
            InstanceRole.MONGO_M5,
            InstanceRole.MONGO_M6,
            InstanceRole.MONGO_M7,
            InstanceRole.MONGO_M8,
            InstanceRole.MONGO_M9,
            InstanceRole.MONGO_M10,
        ],
        machine_type=MachineType.MONOG_CONFIG,
        group_name=_("ConfigServer 节点"),
    )
    _dummy, shard_group = graph.add_instance_nodes_with_machinetype(
        cluster=cluster,
        roles=[
            InstanceRole.MONGO_M1,
            InstanceRole.MONGO_M2,
            InstanceRole.MONGO_M3,
            InstanceRole.MONGO_M4,
            InstanceRole.MONGO_M5,
            InstanceRole.MONGO_M6,
            InstanceRole.MONGO_M7,
            InstanceRole.MONGO_M8,
            InstanceRole.MONGO_M9,
            InstanceRole.MONGO_M10,
        ],
        machine_type=MachineType.MONGODB,
        group_name=_("Shard 节点"),
    )
    _dummy, backup_group = graph.add_instance_nodes_with_machinetype(
        cluster=cluster, roles=InstanceRole.MONGO_BACKUP, machine_type=MachineType.MONGODB, group_name=_("Backup 节点")
    )

    # 获得访问入口节点组
    entry = mongos_insts.first().bind_entry.first()
    _dummy, entry_group = graph.add_node(entry)

    # 访问入口 ----> Mongos节点，关系为：访问
    graph.add_line(source=entry_group, target=mongos_group, label=LineLabel.Access)

    graph.add_line(source=mongos_group, target=configs_group, label=LineLabel.Access)
    graph.add_line(source=mongos_group, target=shard_group, label=LineLabel.ReadWrite)

    graph.add_line(source=configs_group, target=shard_group, label=LineLabel.Access)
    graph.add_line(source=configs_group, target=backup_group, label=LineLabel.Access)

    graph.add_line(source=shard_group, target=backup_group, label=LineLabel.Access)

    return graph
