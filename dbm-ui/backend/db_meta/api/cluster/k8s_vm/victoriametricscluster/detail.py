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

from backend.components.kubernetes.client import KubernetesApi
from backend.db_meta.api.cluster.base.graph import Graphic, Group, LineLabel
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.utils.k8s_db.vm.consts import (
    COMPONENT_VMINSERT,
    COMPONENT_VMSELECT,
    COMPONENT_VMSTORAGE,
    VMINSERT_PORT,
    VMSELECT_PORT,
)


def scan_cluster(
    cluster: Cluster,
    k8s_cluster_name: str,
    namespace: str,
) -> Graphic:
    def _get_component_instances(component_name: str) -> list:
        data = {
            "k8sClusterName": k8s_cluster_name,
            "clusterName": cluster.name,
            "namespace": namespace,
            "componentName": component_name,
        }
        resp = KubernetesApi.component_pods(data, use_admin=True)
        return [
            {"component_name": component_name, "pod_name": item["podName"], "status": item["status"]}
            for item in resp.get("result", [])
        ]

    write_entry = (
        cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.CLBDNS,
            role=ClusterEntryRole.MASTER_ENTRY.value,
        ).first()
        or cluster.clusterentry_set.filter(role=ClusterEntryRole.MASTER_ENTRY.value).first()
    )
    query_entry = (
        cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.CLBDNS,
            role=ClusterEntryRole.SLAVE_ENTRY.value,
        ).first()
        or cluster.clusterentry_set.filter(role=ClusterEntryRole.SLAVE_ENTRY.value).first()
    )
    graph = Graphic(
        node_id=f"{write_entry.entry}:{VMINSERT_PORT}" if write_entry else Graphic.generate_graphic_id(cluster)
    )

    write_entry_group = Group(node_id="vminsert_entry_group", group_name=_("写入入口"))
    query_entry_group = Group(node_id="vmselect_entry_group", group_name=_("查询入口"))
    if write_entry:
        write_node, write_entry_group = graph.add_node(write_entry, to_group=write_entry_group)
        write_node.node_id = f"{write_node.node_id}:{VMINSERT_PORT}"
        write_entry_group.children_id = [write_node.node_id]
    if query_entry:
        query_node, query_entry_group = graph.add_node(query_entry, to_group=query_entry_group)
        query_node.node_id = f"{query_node.node_id}:{VMSELECT_PORT}"
        query_entry_group.children_id = [query_node.node_id]
    storage_instances = list(cluster.storageinstance_set.filter(instance_role=InstanceRole.VM_STORAGE.value))

    vminsert_group = Group(node_id=COMPONENT_VMINSERT, group_name="VMInsert")
    for instance in _get_component_instances(COMPONENT_VMINSERT):
        graph.add_node(instance, to_group=vminsert_group)

    vmselect_group = Group(node_id=COMPONENT_VMSELECT, group_name="VMSelect")
    for instance in _get_component_instances(COMPONENT_VMSELECT):
        graph.add_node(instance, to_group=vmselect_group)

    vmstorage_group = Group(node_id=COMPONENT_VMSTORAGE, group_name="VMStorage")
    for instance in _get_component_instances(COMPONENT_VMSTORAGE):
        graph.add_node(instance, to_group=vmstorage_group)

    graph.add_line(source=write_entry_group, target=vminsert_group, label=LineLabel.Bind)
    graph.add_line(source=vminsert_group, target=vmstorage_group, label=LineLabel.Bind)
    if storage_instances:
        storage_entry_group = Group(
            node_id=f"vmstorage_entry_group:{storage_instances[0].port}",
            group_name=_("存储入口"),
        )
        for storage_instance in storage_instances:
            graph.add_node(storage_instance, to_group=storage_entry_group)
        graph.add_line(source=storage_entry_group, target=vmstorage_group, label=LineLabel.Bind)
    graph.add_line(source=query_entry_group, target=vmselect_group, label=LineLabel.Bind)
    graph.add_line(source=vmselect_group, target=vmstorage_group, label=LineLabel.Bind)
    return graph
