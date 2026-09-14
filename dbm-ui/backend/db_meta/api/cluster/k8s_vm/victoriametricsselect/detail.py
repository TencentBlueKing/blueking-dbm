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
from backend.db_meta.enums import ClusterEntryRole, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.utils.k8s_db.vm.consts import COMPONENT_VMSELECT, VMSELECT_PORT


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

    query_entry = cluster.clusterentry_set.filter(role=ClusterEntryRole.SLAVE_ENTRY.value).first()
    graph = Graphic(
        node_id=f"{query_entry.entry}:{VMSELECT_PORT}" if query_entry else Graphic.generate_graphic_id(cluster)
    )

    entry_group = Group(node_id="vmselect_entry_group", group_name=_("查询入口"))
    if query_entry:
        query_node, entry_group = graph.add_node(query_entry, to_group=entry_group)
        query_node.node_id = f"{query_node.node_id}:{VMSELECT_PORT}"
        entry_group.children_id = [query_node.node_id]

    vmselect_group = Group(node_id=COMPONENT_VMSELECT, group_name="VMSelect")
    for vmselect in _get_component_instances(COMPONENT_VMSELECT):
        graph.add_node(vmselect, to_group=vmselect_group)

    vmstorage_group = Group(node_id="external_vmstorage", group_name=_("外部 VMStorage"))
    for vmstorage in cluster.storageinstance_set.filter(instance_role=InstanceRole.VM_STORAGE.value):
        graph.add_node(vmstorage, to_group=vmstorage_group)

    graph.add_line(source=entry_group, target=vmselect_group, label=LineLabel.Bind)
    graph.add_line(source=vmselect_group, target=vmstorage_group, label=LineLabel.Bind)
    return graph
