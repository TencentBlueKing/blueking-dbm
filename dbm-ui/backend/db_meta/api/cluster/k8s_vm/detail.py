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
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType
from backend.db_meta.models import Cluster
from backend.flow.utils.k8s_db.vm.consts import COMPONENT_VMINSERT, COMPONENT_VMSELECT, COMPONENT_VMSTORAGE


def scan_cluster(
    cluster: Cluster,
    k8s_cluster_name: str,
    namespace: str,
) -> Graphic:
    vminsert_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.CLBDNS,
        role=ClusterEntryRole.MASTER_ENTRY.value,
    ).first()
    vmselect_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.CLBDNS,
        role=ClusterEntryRole.SLAVE_ENTRY.value,
    ).first()
    graph = Graphic(node_id=vminsert_entry.entry if vminsert_entry else Graphic.generate_graphic_id(cluster))

    vminsert_entry_group = Group(node_id="vminsert_entry_group", group_name=_("写访问入口"))
    vmselect_entry_group = Group(node_id="vmselect_entry_group", group_name=_("读访问入口"))
    if vminsert_entry:
        graph.add_node(vminsert_entry, to_group=vminsert_entry_group)
    if vmselect_entry:
        graph.add_node(vmselect_entry, to_group=vmselect_entry_group)

    def get_instances(component_name: str) -> list:
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

    component_groups = {}
    for component_name, group_name in [
        (COMPONENT_VMINSERT, "VMInsert"),
        (COMPONENT_VMSELECT, "VMSelect"),
        (COMPONENT_VMSTORAGE, "VMStorage"),
    ]:
        component_group = Group(node_id=component_name, group_name=group_name)
        for instance in get_instances(component_name):
            graph.add_node(instance, to_group=component_group)
        component_groups[component_name] = component_group

    graph.add_line(source=vminsert_entry_group, target=component_groups[COMPONENT_VMINSERT], label=LineLabel.Access)
    graph.add_line(source=vmselect_entry_group, target=component_groups[COMPONENT_VMSELECT], label=LineLabel.Access)
    graph.add_line(
        source=component_groups[COMPONENT_VMINSERT],
        target=component_groups[COMPONENT_VMSTORAGE],
        label=LineLabel.ReadWrite,
    )
    graph.add_line(
        source=component_groups[COMPONENT_VMSELECT],
        target=component_groups[COMPONENT_VMSTORAGE],
        label=LineLabel.ReadWrite,
    )
    return graph
