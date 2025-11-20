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

from backend.db_meta.api.cluster.base.graph import ForeignRelationType, Graphic, Group, LineLabel
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple


def scan_cluster(cluster: Cluster) -> Graphic:
    """
    所有往 error report 中添加的信息都是集群的检查规则
    这部分应该抽象出去独立生成 report
    """
    graph = Graphic(node_id=Graphic.generate_graphic_id(cluster))

    for tr in StorageInstanceTuple.objects.prefetch_related(
        "ejector__cluster",
        "receiver__cluster",
    ).filter(receiver__cluster=cluster, ejector__cluster=cluster):
        ejector_instance = tr.ejector
        receiver_instance = tr.receiver

        ejector_instance_node, ejector_instance_grp = graph.add_node(ejector_instance)

        if ejector_instance.instance_inner_role == InstanceInnerRole.REPEATER:
            receiver_instance_node, receiver_instance_group = graph.add_node(receiver_instance, ejector_instance_grp)
        else:
            receiver_instance_node, receiver_instance_group = graph.add_node(receiver_instance)

        graph.add_line(source=ejector_instance_node, target=receiver_instance_node, label=LineLabel.Rep)
        slave_be_group = Group(node_id="slave_bind_entry_group", group_name=_("访问入口（从）"))
        for slave_be in receiver_instance.bind_entry.all():
            dummy_slave_be_node, slave_be_group = graph.add_node(slave_be, to_group=slave_be_group)
            graph.add_line(source=slave_be_group, target=receiver_instance_group, label=LineLabel.Bind)

        master_be_group = Group(node_id="master_bind_entry_group", group_name=_("访问入口（主）"))
        for be in ejector_instance.bind_entry.all():
            dummy_be_node, master_be_group = graph.add_node(be, to_group=master_be_group)
            graph.add_line(source=master_be_group, target=ejector_instance_grp, label=LineLabel.Bind)

        for otr in StorageInstanceTuple.objects.filter(ejector=ejector_instance).exclude(receiver__cluster=cluster):
            foreign_receiver_cluster = otr.receiver.cluster.get()
            graph.add_foreign_cluster(ForeignRelationType.RepTo, foreign_receiver_cluster)

        for otr in StorageInstanceTuple.objects.filter(receiver=ejector_instance).exclude(ejector__cluster=cluster):
            foreign_ejector_cluster = otr.ejector.cluster.get()
            graph.add_foreign_cluster(ForeignRelationType.RepFrom, foreign_ejector_cluster)

    return graph


def single_scan_cluster(cluster: Cluster) -> Graphic:
    graph = Graphic(node_id=Graphic.generate_graphic_id(cluster))
    storage_inst = StorageInstance.objects.get(cluster=cluster, cluster_type=ClusterType.OracleSingleNone)
    _, cluster_entry_group = graph.add_node(storage_inst.bind_entry.first())
    _, storage_node_group = graph.add_node(storage_inst)
    graph.add_line(source=cluster_entry_group, target=storage_node_group, label=LineLabel.Bind)
    return graph
