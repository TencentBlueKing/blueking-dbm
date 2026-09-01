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
from collections import defaultdict
from functools import reduce
from typing import Dict, List

from django.db.models import Q
from django.utils.translation import gettext as _

from backend.db_meta.api.cluster.base.graph import Graphic, Group, LineLabel, Node
from backend.db_meta.enums import AccessLayer, MachineType, MachineTypeInstanceRoleMap
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource, mongo_shard_name_sort_key

# 拓扑图分片组 id（前端可按此加宽）
MONGODB_SHARDS_GROUP_ID = "mongodb_shards"


def _add_shard_summary_nodes(graph: Graphic, shard_group: Group, shard_to_insts: Dict[str, List[StorageInstance]]):
    """每个分片一行：分片名 / ip:port,ip:port,...（不展示单实例状态噪音）"""
    for shard_name in sorted(shard_to_insts.keys(), key=mongo_shard_name_sort_key):
        members = sorted(shard_to_insts[shard_name], key=lambda i: (i.machine.ip, i.port))
        if not members:
            continue
        addrs = ["{}:{}".format(m.machine.ip, m.port) for m in members]
        node_id = "{} / {}".format(shard_name, ",".join(addrs))
        node = Node(members[0], node_id=node_id, instance_state="")
        if node in graph.nodes:
            continue
        shard_group.add_child(node)
        graph.nodes.append(node)


def scan_cluster(cluster: Cluster) -> Graphic:
    """
    绘制 Mongo Sharded Cluster 拓扑：
    访问入口 → Mongos → ConfigServer
                      → 共 N 分片（每行：shard / addrlist）
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

    # 分片合并为一组：共 N 分片，每行 shard / addrlist
    inst_filter = Q(
        reduce(operator.or_, [Q(instance_role=role) for role in MachineTypeInstanceRoleMap[MachineType.MONGODB]]),
        cluster=cluster,
        machine_type=MachineType.MONGODB,
    )
    insts, inst_id__shard = MongoDBListRetrieveResource.query_storage_shard(inst_filter)

    shard_to_insts: Dict[str, List[StorageInstance]] = defaultdict(list)
    for inst in insts:
        shard_name = inst_id__shard.get(inst.id) or ""
        if not shard_name:
            continue
        shard_to_insts[shard_name].append(inst)

    if shard_to_insts and mongos_group:
        shard_group = graph.get_or_create_group(
            group_id=MONGODB_SHARDS_GROUP_ID,
            group_name=_("共{}分片").format(len(shard_to_insts)),
        )
        _add_shard_summary_nodes(graph, shard_group, shard_to_insts)
        graph.add_line(source=mongos_group, target=shard_group, label=LineLabel.Access)

    # 获得访问入口节点组
    for proxy_instance in cluster.proxyinstance_set.prefetch_related("bind_entry").all():
        entry_group = Group(node_id="master_bind_entry_group", group_name=_("访问入口"))
        for entry in proxy_instance.bind_entry.all():
            _dummy, entry_group = graph.add_node(entry, to_group=entry_group)
            # 访问入口 ----> Mongos节点，关系为：
            graph.add_line(source=entry_group, target=mongos_group, label=LineLabel.Bind)
    # mongos -----> config_svr，关系为：访问
    graph.add_line(source=mongos_group, target=configs_group, label=LineLabel.Access)

    return graph
