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
from functools import reduce
from typing import List

from django.db.models import Q
from django.utils.translation import gettext as _

from backend.db_meta.api.cluster.base.graph import Graphic, LineLabel
from backend.db_meta.enums import AccessLayer, MachineType, MachineTypeInstanceRoleMap
from backend.db_meta.models import Cluster
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource


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

    # 获取mongos节点组
    mongos_insts, mongos_group = graph.add_instance_nodes_with_machine_type(
        cluster=cluster,
        roles=AccessLayer.PROXY,
        machine_type=MachineType.MONGOS,
        group_name=_("Mongos 节点"),
        inst_type="proxy",
    )

    # 获取config_svr节点组
    _dummy, configs_group = graph.add_instance_nodes_with_machine_type(
        cluster=cluster,
        roles=MachineTypeInstanceRoleMap[MachineType.MONOG_CONFIG],
        machine_type=MachineType.MONOG_CONFIG,
        group_name=_("ConfigServer 节点"),
    )

    # 获取各个分片的节点组
    inst_filter = Q(
        reduce(operator.or_, [Q(instance_role=role) for role in MachineTypeInstanceRoleMap[MachineType.MONOG_CONFIG]]),
        cluster=cluster,
        machine_type=MachineType.MONGODB,
    )
    insts, inst_id__shard = MongoDBListRetrieveResource.query_storage_shard(inst_filter)

    shard_groups: List[str] = []
    for inst in insts:
        shard_group_name = _("分片{} 节点").format(inst_id__shard[inst.id])
        shard_group = graph.get_or_create_group(group_id=shard_group_name, group_name=shard_group_name)
        graph.add_node(ins=inst, to_group=shard_group)
        # mongos -----> 各个shard，关系为：访问
        if shard_group_name not in shard_groups:
            graph.add_line(source=mongos_group, target=shard_group, label=LineLabel.Access)
            shard_groups.append(shard_group_name)

    # 获得访问入口节点组
    entry = mongos_insts.first().bind_entry.first()
    _dummy, entry_group = graph.add_node(entry)

    # 访问入口 ----> Mongos节点，关系为：域名绑定
    graph.add_line(source=entry_group, target=mongos_group, label=LineLabel.Bind)
    # mongos -----> config_svr，关系为：访问
    graph.add_line(source=mongos_group, target=configs_group, label=LineLabel.Access)

    return graph
